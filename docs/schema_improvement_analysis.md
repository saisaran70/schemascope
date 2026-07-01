# Med360 — Schema Improvement Analysis

Covers all three apps (Patient, Doctor, MCO). Each issue is categorised by priority,
includes the exact fix, and states the database impact and migration risk.

---

## Priority Legend

| Priority | Meaning |
|---|---|
| 🔴 Critical | Feature is completely broken or data is being lost right now |
| 🟠 High | Feature is partially broken or data integrity is at risk |
| 🟡 Medium | Design flaw that will cause problems as the product scales |
| 🟢 Low | Good practice — improve resilience, clarity, and performance |

---

## Priority 1 — 🔴 Critical (Feature Broken / Data Loss)

---

### 1.1 · `bookings.service_id` — Single FK blocks multi-service bookings

**Issue**
`bookings` has one `service_id` column. The Patient and MCO apps both allow adding
multiple services to a single home-care booking. Today only the first service is
saved; the rest are silently dropped.

**Fix — Add `booking_items` table**
```sql
CREATE TABLE booking_items (
  id            SERIAL PRIMARY KEY,
  booking_id    INT NOT NULL REFERENCES bookings(id),
  service_id    INT NOT NULL REFERENCES services(id),
  quantity      INT NOT NULL DEFAULT 1,
  unit_price    NUMERIC(10,2),
  discount      NUMERIC(10,2) DEFAULT 0,
  notes         TEXT,
  created_at    TIMESTAMP DEFAULT NOW(),
  updated_at    TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_booking_items_booking ON booking_items(booking_id);
```
Migrate existing data: `INSERT INTO booking_items(booking_id, service_id, unit_price) SELECT id, service_id, price FROM bookings WHERE service_id IS NOT NULL`.

**Database Impact** — New table. `bookings.service_id` can be kept as a legacy
denormalized column (readable for old queries) and deprecated gradually.
**Migration Risk** — 🟡 Medium — all API endpoints that write `service_id` must also
write to `booking_items`.

---

### 1.2 · `otps` — Three OTP flows share one table with no type discriminator

**Issue**
The same table serves login OTPs (6-digit), service-start OTPs (4-digit), and
service-completion OTPs (4-digit). There is no `type` or `booking_id` column.
A patient's login OTP can accidentally validate a service-start event.

**Fix — Add two columns**
```sql
ALTER TABLE otps ADD COLUMN type VARCHAR(20) DEFAULT 'LOGIN';
-- Values: LOGIN | SERVICE_START | SERVICE_COMPLETE
ALTER TABLE otps ADD COLUMN booking_id INT REFERENCES bookings(id);
CREATE INDEX idx_otps_booking ON otps(booking_id);
```
Backfill: `UPDATE otps SET type = 'LOGIN' WHERE booking_id IS NULL`.

**Database Impact** — Two new columns on a lightweight table (OTPs expire quickly,
so row count is always small).
**Migration Risk** — 🔴 High — auth and MCO service-start flows must be updated
simultaneously or a security gap opens.

---

### 1.3 · `notifications.is_read` / `type` — Read state and categories missing

**Issue**
"Unread" badge count, "Mark All Read", and notification category filters (Booking,
Reminder, Inventory Alert) are all rendered in the UI but have no schema backing.
Every app restart re-shows all notifications as unread.

**Fix — Add three columns**
```sql
ALTER TABLE notifications ADD COLUMN is_read     BOOLEAN DEFAULT false;
ALTER TABLE notifications ADD COLUMN read_at      TIMESTAMP;
ALTER TABLE notifications ADD COLUMN type         VARCHAR(50);
-- Values: BOOKING_UPDATE | REMINDER | INVENTORY_ALERT | PAYMENT | SYSTEM
```
> Note: `notifications` is a MongoDB collection — add via `$set` migration script.

**Database Impact** — Three fields on the notifications collection. Index on `(userId, is_read)` recommended.
**Migration Risk** — 🟡 Medium — MongoDB schema-less so no migration required; just
update the write path.

---

### 1.4 · `mco_slots_availability.mcoId` — NULL for all 7 rows

**Issue**
`SELECT * FROM slots_availability WHERE mcoId IS NOT NULL` returns 0 rows.
The MCO app cannot match a slot to an MCO, making the entire slot-booking
pipeline for home-care services non-functional.

**Fix — Data patch + constraint**
```sql
-- Step 1: investigate which MCO each service belongs to via mco_services
UPDATE slots_availability sa
SET "mcoId" = ms.mco_id
FROM mco_services ms
WHERE ms.service_id = sa.service_id
  AND sa."mcoId" IS NULL;

-- Step 2: add NOT NULL constraint once backfill is confirmed
ALTER TABLE slots_availability ALTER COLUMN "mcoId" SET NOT NULL;
```

**Database Impact** — Data-only change. No structural migration.
**Migration Risk** — 🟢 Low — but confirm the service↔MCO mapping before patching.

---

### 1.5 · `chat_messages.is_read` / `delivery_status` — Message state lost

**Issue**
"Mark all read" button and unread badge count on the MCO chat screen have no
schema backing. Delivery states (sent / delivered / read) are also untracked.

**Fix**
```sql
-- MongoDB collection update
db.chat_messages.updateMany({}, { $set: { is_read: false, delivery_status: "SENT" } })
-- delivery_status values: SENT | DELIVERED | READ
```

**Database Impact** — Two fields on `chat_messages`. Add index on `(conversationId, is_read)`.
**Migration Risk** — 🟢 Low.

---

## Priority 2 — 🟠 High (Data Integrity / Partial Breakage)

---

### 2.1 · `payments.status` — Corrupted gateway JSON stored as status value

**Issue**
Live data shows:
```
"key":"riZumF"     ← Razorpay JSON fragment stored in status column
"unmappedstatus":"captured"
```
These are gateway response payloads leaking into the `status` column. Any
query filtering `WHERE status = 'SUCCESS'` misses these payments.

**Fix**
```sql
-- Step 1: clean up corrupted rows
UPDATE payments
SET status = 'PENDING'
WHERE status NOT IN ('PENDING','SUCCESS','FAILED','REFUNDED');

-- Step 2: add a CHECK constraint to prevent future corruption
ALTER TABLE payments
ADD CONSTRAINT chk_payment_status
CHECK (status IN ('PENDING','SUCCESS','FAILED','REFUNDED'));
```

**Database Impact** — Data correction + new constraint. 16 rows need review.
**Migration Risk** — 🟡 Medium — confirm with payment team which corrupted rows
should be SUCCESS vs FAILED before patching.

---

### 2.2 · `bookings.status` and `bookings.type` — Numeric garbage values

**Issue**
Live data contains:
- `status = "960"` (1 row)
- `type = "0"` (1 row), `type = "14"` (2 rows)

These are not valid enum values and will crash any API endpoint that relies on
enum parsing.

**Fix**
```sql
-- Inspect the rows first
SELECT id, status, type, created_at FROM bookings
WHERE status = '960' OR type IN ('0','14');

-- After review, correct or delete
UPDATE bookings SET status = 'CANCELLED' WHERE status = '960';
UPDATE bookings SET type = NULL WHERE type IN ('0','14');

-- Add CHECK constraints
ALTER TABLE bookings
ADD CONSTRAINT chk_booking_status
CHECK (status IN ('INITIATED','BOOKED','ACCEPTED','DECLINED','ON_ROUTE',
                  'ARRIVED','IN_PROGRESS','COMPLETED','CANCELLED','EXPIRED'));

ALTER TABLE bookings
ADD CONSTRAINT chk_booking_type
CHECK (type IN ('VIDEO','INSTA_CONSULTATION','HOME_CARE_SERVICE',
                'SPECIALIST_CONSULTATION','SECOND_OPINION'));
```

**Database Impact** — 4 rows corrected + 2 new CHECK constraints.
**Migration Risk** — 🟢 Low after the data review.

---

### 2.3 · `patient_settings` — 91.8 % of patients have no settings row

**Issue**
Only 4 rows exist for 49 patients. If the app reads settings and gets NULL, it
either crashes or silently uses a hard-coded default — meaning per-patient
preferences are never actually persisted.

**Fix — Backfill + trigger**
```sql
-- Backfill missing rows with sensible defaults
INSERT INTO settings (patient_id, push_notification, email_notification,
  sms_notification, booking_reminders, promotional_offers, dark_mode,
  language, created_at, updated_at)
SELECT id, true, true, true, true, false, false, 'en', NOW(), NOW()
FROM patients p
WHERE NOT EXISTS (SELECT 1 FROM settings s WHERE s.patient_id = p.id);

-- Add trigger so every new patient auto-gets a settings row
CREATE OR REPLACE FUNCTION fn_create_patient_settings()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO settings(patient_id, created_at, updated_at)
  VALUES (NEW.id, NOW(), NOW())
  ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patient_settings
AFTER INSERT ON patients
FOR EACH ROW EXECUTE FUNCTION fn_create_patient_settings();
```

**Database Impact** — 45 rows inserted. Trigger adds ~0.1 ms to patient creation.
**Migration Risk** — 🟢 Low.

---

### 2.4 · `doctors.modes` — Multi-value stored as a comma-separated string

**Issue**
Live data: `"VIDEO"`, `"VIDEO,CLINIC"`. This makes querying ("find all doctors
who do CLINIC consultations") require a `LIKE '%CLINIC%'` — no index can be
used, queries are slow, and values can drift in casing or spelling.

**Fix — Normalize into a junction table**
```sql
CREATE TABLE doctor_modes (
  doctor_id  INT NOT NULL REFERENCES doctors(id),
  mode       VARCHAR(30) NOT NULL,  -- VIDEO | CLINIC | HOME_VISIT
  PRIMARY KEY (doctor_id, mode)
);

-- Migrate existing data
INSERT INTO doctor_modes (doctor_id, mode)
SELECT id, TRIM(UNNEST(STRING_TO_ARRAY(modes, ',')))
FROM doctors
WHERE modes IS NOT NULL AND modes <> '';
```
Keep `doctors.modes` as a read-only deprecated column until all API consumers are updated.

**Database Impact** — New small table (~30 rows currently). Enables indexed queries on consultation mode.
**Migration Risk** — 🟡 Medium — API write paths must be updated.

---

### 2.5 · `mcos.specialization` — Always an empty string

**Issue**
All 8 MCO rows have `specialization = ""`. The MCO app's service filter relies
on this to show relevant MCOs for a specialization. The column is a free-text
field with no FK — even if populated, it can't join to `specializations`.

**Fix**
```sql
ALTER TABLE mcos ADD COLUMN specialization_id INT REFERENCES specializations(id);
-- Populate manually after reviewing which specialization each MCO covers
-- Then drop the old text column once migration is complete
ALTER TABLE mcos DROP COLUMN specialization;
```

**Database Impact** — Column type change + new FK.
**Migration Risk** — 🟡 Medium — requires manual data entry for specialization mapping.

---

### 2.6 · Missing `updated_at` on several tables

**Issue**
`health_records`, `callback_requests`, `documents`, `doctor_expertise`,
`doctor_languages` have no `updated_at` column. Any soft-update (e.g. marking
a health record inactive) is invisible to sync or audit logic.

**Fix**
```sql
ALTER TABLE health_records     ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
ALTER TABLE callback_requests  ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
ALTER TABLE documents          ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
```

**Database Impact** — Additive only. Existing rows get `NOW()` as the default.
**Migration Risk** — 🟢 Low.

---

## Priority 3 — 🟡 Medium (Normalization & Design)

---

### 3.1 · `doctors` clinic fields — Unstructured clinic data inside the doctor row

**Issue**
`doctors` has `clinic_name`, `clinic_address_1`, `clinic_address_2`, `hospital`
as flat columns. A doctor can practice at multiple clinics; this schema limits
them to one and mixes identity data with location data.

**Fix — Extract into `clinics` table**
```sql
CREATE TABLE clinics (
  id           SERIAL PRIMARY KEY,
  doctor_id    INT NOT NULL REFERENCES doctors(id),
  name         VARCHAR(200),
  address_1    VARCHAR(300),
  address_2    VARCHAR(300),
  city         VARCHAR(100),
  latitude     NUMERIC(9,6),
  longitude    NUMERIC(9,6),
  is_primary   BOOLEAN DEFAULT false,
  active       BOOLEAN DEFAULT true,
  created_at   TIMESTAMP DEFAULT NOW(),
  updated_at   TIMESTAMP DEFAULT NOW()
);
```

**Database Impact** — New table. Doctors can now have multiple practice locations.
**Migration Risk** — 🟡 Medium.

---

### 3.2 · `patients.uhid` — UHID shown in invoices but not stored in patients

**Issue**
Invoices display `SIMS-PT-000049` (patient UHID) but `patients` has no `uhid`
column. The invoice value is hardcoded or computed at render time — it can
drift out of sync.

**Fix**
```sql
ALTER TABLE patients ADD COLUMN uhid VARCHAR(30) UNIQUE;
-- Auto-generate: SIMS-PT-{LPAD(id::text, 6, '0')}
UPDATE patients SET uhid = 'SIMS-PT-' || LPAD(id::text, 6, '0');
```

**Database Impact** — One column. Existing invoices remain consistent via backfill.
**Migration Risk** — 🟢 Low.

---

### 3.3 · `patients.is_phone_verified` and `doctors.is_verified` — Missing verification flags

**Issue**
Both apps show a "Verified ✓" badge but there is no boolean column backing it.
The badge is either always shown (false confidence) or never shown (broken UI).

**Fix**
```sql
ALTER TABLE patients ADD COLUMN is_phone_verified BOOLEAN DEFAULT false;
ALTER TABLE doctors  ADD COLUMN is_verified        BOOLEAN DEFAULT false;
ALTER TABLE doctors  ADD COLUMN managed_by_admin   BOOLEAN DEFAULT false;
ALTER TABLE doctors  ADD COLUMN doctor_type        VARCHAR(50);
-- doctor_type: GENERAL_PRACTITIONER | SPECIALIST | INSTA_ONLY
```

**Database Impact** — Additive columns.
**Migration Risk** — 🟢 Low.

---

### 3.4 · `family_members.mobile` — No way to contact a family member

**Issue**
Booking confirmation and SMS/WhatsApp notifications need a phone number for
the family member. Currently only the patient's mobile can be used, causing
notifications for a family member's booking to go to the wrong person.

**Fix**
```sql
ALTER TABLE family_members ADD COLUMN mobile VARCHAR(15);
ALTER TABLE family_members ADD COLUMN email  VARCHAR(200);
```

**Database Impact** — Additive.
**Migration Risk** — 🟢 Low.

---

### 3.5 · `addresses` — Missing `receiver_name` and `receiver_phone`

**Issue**
The Patient app collects "Receiver Details" at checkout (name + phone of the
person who will receive the MCO nurse at the address). These fields are shown
in the UI but discarded — MCO nurses arrive with no contact details.

**Fix**
```sql
ALTER TABLE addresses ADD COLUMN receiver_name  VARCHAR(100);
ALTER TABLE addresses ADD COLUMN receiver_phone VARCHAR(15);
```

**Database Impact** — Additive.
**Migration Risk** — 🟢 Low.

---

### 3.6 · `callback_requests` — Only 2 columns for a full support workflow

**Issue**
The table has only `patient_id` and `created_at`. The "Report Issue / Request
Callback" feature needs reason, assignment, scheduling, and resolution tracking.

**Fix**
```sql
ALTER TABLE callback_requests ADD COLUMN reason         TEXT;
ALTER TABLE callback_requests ADD COLUMN status         VARCHAR(20) DEFAULT 'OPEN';
-- status: OPEN | ASSIGNED | SCHEDULED | RESOLVED | CLOSED
ALTER TABLE callback_requests ADD COLUMN priority       VARCHAR(10) DEFAULT 'NORMAL';
ALTER TABLE callback_requests ADD COLUMN assigned_to    INT REFERENCES users(id);
ALTER TABLE callback_requests ADD COLUMN scheduled_time TIMESTAMP;
ALTER TABLE callback_requests ADD COLUMN resolved_at    TIMESTAMP;
ALTER TABLE callback_requests ADD COLUMN updated_at     TIMESTAMP DEFAULT NOW();
```

**Database Impact** — 6 columns on a table with only 4 rows — no risk.
**Migration Risk** — 🟢 Low.

---

### 3.7 · `tokbox_sessions` — No call timestamps or duration

**Issue**
The video call UI shows a live duration counter but it is never saved. Post-call
audit, billing for extended calls, and support investigations all need this data.

**Fix**
```sql
-- MongoDB collection
db.tokbox_sessions.updateMany({}, {
  $set: { call_start_time: null, call_end_time: null, call_duration_seconds: null }
})
```

**Database Impact** — 3 fields on 274 existing documents.
**Migration Risk** — 🟢 Low.

---

### 3.8 · `health_records` — Typo in column name `family_memeber_id`

**Issue**
`family_memeber_id` (double-e) is the existing column name. Any code using the
correct spelling `family_member_id` silently inserts NULL.

**Fix**
```sql
ALTER TABLE health_records
RENAME COLUMN family_memeber_id TO family_member_id;
```
> Update all ORM models, API controllers, and query strings after renaming.

**Database Impact** — Column rename only. Data is preserved.
**Migration Risk** — 🟠 High (coordination) — every consumer must be updated atomically.

---

## Priority 4 — 🟢 Low (Performance & Indexes)

`bookings` is queried by every module on nearly every screen. None of its
foreign-key columns are indexed in the current SQLite export.

### 4.1 · Missing indexes on `bookings`

```sql
CREATE INDEX idx_bookings_patient    ON bookings(patient_id);
CREATE INDEX idx_bookings_doctor     ON bookings(doctor_id);
CREATE INDEX idx_bookings_mco        ON bookings(mco_id);
CREATE INDEX idx_bookings_status     ON bookings(status);
CREATE INDEX idx_bookings_date       ON bookings(booked_date);
CREATE INDEX idx_bookings_type       ON bookings(type);
```

**Impact** — Composite queries like "all ACCEPTED bookings for a patient today"
go from full-table-scan to index lookup. Critical once `bookings` exceeds ~10,000 rows.

### 4.2 · Missing indexes on supporting tables

```sql
CREATE INDEX idx_prescriptions_booking  ON prescriptions(booking_id);
CREATE INDEX idx_prescriptions_patient  ON prescriptions(patient_id);
CREATE INDEX idx_medications_booking    ON medications(booking_id);
CREATE INDEX idx_samples_booking        ON patient_samples(booking_id);
CREATE INDEX idx_timeline_booking       ON bookings_timeline(booking_id);
CREATE INDEX idx_payments_patient       ON payments(patient_id);
CREATE INDEX idx_payments_status        ON payments(status);
CREATE INDEX idx_documents_booking      ON documents(booking_id);
```

---

## Priority 5 — Missing Tables (New Feature Enablement)

These tables are fully absent and block entire product features.

| # | Table | Blocks | Impact |
|---|---|---|---|
| 1 | `booking_items` | Multi-service cart, MCO extra services | 🔴 Critical |
| 2 | `vitals` | MedTel structured readings (BP, Sugar, BMI) | 🟠 High |
| 3 | `referral_wallet` + `referral_transactions` | Referral earnings & payouts | 🟠 High |
| 4 | `checklist_completions` | MCO protocol checklist per booking | 🟠 High |
| 5 | `weekly_schedule` / `recurring_slots` | Doctor "every Monday 9am" availability | 🟠 High |
| 6 | `issue_reports` | Patient "Report an Issue" form | 🟡 Medium |
| 7 | `search_history` | Patient "Recent Searches" persistence | 🟡 Medium |
| 8 | `device_readings` | MCO connected-device vitals (BP monitor, glucometer) | 🟡 Medium |
| 9 | `break_schedule` | MCO lunch/break slots in daily schedule | 🟡 Medium |
| 10 | `mco_performance_snapshots` | Week-over-week MCO metrics | 🟡 Medium |
| 11 | `login_attempts` | Auth audit trail for MCO and doctor | 🟡 Medium |
| 12 | `ai_sessions` / `ai_queries` | AI Specialist Finder and Health Assistant | 🟢 Low |
| 13 | `quick_message_templates` | MCO in-app chat canned replies | 🟢 Low |

---

## Consolidated Impact Summary

| Priority | Issue Count | Rows/Tables Affected | Max Risk |
|---|---|---|---|
| 🔴 Critical | 5 | `booking_items` (new), `otps`, `notifications`, `slots_availability`, `chat_messages` | High |
| 🟠 High | 6 | `payments`, `bookings`, `patient_settings`, `doctors.modes`, `mcos`, timestamps | Medium |
| 🟡 Medium | 8 | `clinics` (new), `patients`, `doctors`, `family_members`, `addresses`, `callback_requests`, `tokbox_sessions`, `health_records` | Low–Medium |
| 🟢 Low | 2 | Indexes on `bookings` and 4 supporting tables | None |
| Missing Tables | 13 | New tables required | New builds |

---

## Recommended Execution Order

```
Sprint 1 — Fix broken features (zero data loss risk)
  ├── 1.4  Patch mco_slots_availability.mcoId NULLs
  ├── 2.2  Clean bookings.status / type garbage values
  ├── 2.1  Clean payments.status corrupted rows + add CHECK constraint
  └── 2.3  Backfill patient_settings (45 missing rows)

Sprint 2 — Add missing columns (additive, no breakage)
  ├── 1.2  otps.type + otps.booking_id
  ├── 1.3  notifications.is_read, read_at, type
  ├── 1.5  chat_messages.is_read, delivery_status
  ├── 2.6  health_records / callback_requests / documents.updated_at
  ├── 3.2  patients.uhid
  ├── 3.3  patients.is_phone_verified, doctors.is_verified
  ├── 3.4  family_members.mobile, email
  └── 3.5  addresses.receiver_name, receiver_phone

Sprint 3 — Schema changes (require API coordination)
  ├── 2.4  doctor_modes junction table
  ├── 2.5  mcos.specialization → FK
  ├── 3.1  clinics table extracted from doctors
  ├── 3.6  callback_requests full columns
  └── 3.7  tokbox_sessions call timestamps

Sprint 4 — High-risk rename (all consumers updated together)
  └── 3.8  health_records.family_memeber_id → family_member_id

Sprint 5 — New feature tables
  └── booking_items, vitals, referral_wallet, checklist_completions, weekly_schedule, …

Sprint 6 — Performance
  └── All indexes on bookings and supporting tables
```
