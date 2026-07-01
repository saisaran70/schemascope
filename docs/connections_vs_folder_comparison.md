# Comparison — `patient_doctor_mco_connections.md` vs `mco_slots_availability/` folder

---

## 1. Tables Present in Both

### `bookings`
| What | In connections doc | In folder (`booking_bookings.csv`) |
|---|---|---|
| Row count | 1,025 | 1,025 ✓ |
| `booked_time` format | Not specified | **Integer minutes from midnight** (e.g. 900 = 15:00, 630 = 10:30) — not documented in connections doc |
| `distance` / `eta` format | "MCO home visit logistics" | **Stored as strings**: `"11.77 km"`, `"18 min"` — not documented in connections doc |
| All columns | ✓ present | ✓ match |

### `bookings_timeline`
| What | In connections doc | In folder (`booking_bookings_timeline.csv`) |
|---|---|---|
| Row count | 3,763 | Matches (same data) ✓ |
| `status` values listed | Not listed | Reveals MCO-specific values not in doc: **`ON_ROUTE`** (nurse dispatched), **`ARRIVED`** (nurse on site) — in addition to standard PENDING/IN_PROGRESS/COMPLETED/CANCELLED |

### `recurring_bookings`
| What | In connections doc | In folder (`booking_recurring_bookings.csv`) |
|---|---|---|
| Row count | 6 | 6 ✓ |
| `booked_time` format | Not specified | **Integer minutes from midnight** (e.g. 165, 375, 215) — same as bookings.booked_time |
| `booked_date` values | Not noted | **Test/future dates (2028)** — data quality flag |

### `mco_slots_availability`
| What | In connections doc | In folder (`mco_slots_availability.csv`) |
|---|---|---|
| Row count | **7 rows** | **16 rows** — data has grown, doc is stale |
| `mcoId` issue | NULL for all 7 rows | **Still empty for all 16 rows** — issue persists |
| `time_slot_id` target | `→ time_slots.id` | Points to `mco_time_slots` table (see Section 2 below) |

---

## 2. Tables in the Folder NOT documented in `patient_doctor_mco_connections.md`

### `mco_time_slots` (`mco_time_slots.csv`) — 29 rows
Referenced in `mco_slots_availability.time_slot_id` and `doctor_slots_availability.time_slot_id` but never documented.

| Column | Notes |
|---|---|
| `id` | PK |
| `start_min` | Start of slot in minutes from midnight (e.g. 540 = 09:00) |
| `end_min` | End of slot in minutes from midnight (e.g. 570 = 09:30) |
| `active` | 0/1 |

> This is the lookup table behind every time-slot FK in the system. Its minute-offset format is what drives `bookings.booked_time` and `recurring_bookings.booked_time`.

---

### `mcos` (`mco_mcos.csv`) — 9 rows
Connections doc only references `mcos.id` as a FK target. The actual table structure is never documented.

| Column | Notes |
|---|---|
| `id` | PK |
| `user_map_id` | → `users._id` (auth, UUID) |
| `first_name` / `last_name` | |
| `email` / `mobile` | |
| `dob` | |
| `aadhar_number` | Government ID |
| `experience` | Years |
| `gender` | M / F |
| `location` | City text |
| `rating` | Numeric |
| `registration_number` | Professional reg. |
| `status` | `online` / `offline` |
| `specialization` | |
| `profile_pic` | |
| `last_login` | |
| `created_at` / `updated_at` | |

---

### `services` (`mco_services.csv`) — 55+ rows
Connections doc references `services.id` as FK target but never documents the table. Three columns directly control which other connection tables get populated:

| Column | Notes |
|---|---|
| `id` | PK |
| `name` / `description` | |
| `service_type_id` | → `service_types.id` |
| `service_category_id` | → `service_categories.id` |
| `price` | |
| `type` | `diagnostic` / `routine` / `emergency` |
| **`mco_involved`** | **0/1 — when 1, booking must carry an `mco_id`** |
| **`sample_collection`** | **0/1 — when 1, triggers `patient_samples` flow** |
| `service_time_in_minutes` | |
| `available` | 0/1 |
| `rating` / `reviews` / `bookings` | Denormalized aggregates |
| `tag` / `icon` / `duration` | Display metadata |
| `active` | 0/1 |
| `created_at` / `updated_at` | |

---

## 3. Tables in `patient_doctor_mco_connections.md` NOT in the folder

These tables are fully documented in the connections doc but have no corresponding file in `mco_slots_availability/`:

| Table | Section in doc |
|---|---|
| `prescriptions` | Section 2 — Patient ↔ Doctor |
| `medications` | Section 2 — Patient ↔ Doctor |
| `medical_histories` | Section 2 — Patient ↔ Doctor |
| `patient_referred` | Section 2 — Patient ↔ Doctor |
| `recommendations` | Section 2 — Patient ↔ Doctor |
| `doctor_slots_availability` | Section 2 — Patient ↔ Doctor |
| `reviews` (empty) | Section 2 — Patient ↔ Doctor |
| `mco_reviews` | Section 3 — Patient ↔ MCO |
| `mco_services` (junction) | Section 3 — Patient ↔ MCO |
| `patient_samples` | Section 3 — Patient ↔ MCO |
| `patient_sample_notes` | Section 3 — Patient ↔ MCO |
| `documents` | Section 4 — Shared Documents |
| `payments` | Section 5 — Payment Bridge |
| `payment_bookings` | Section 5 — Payment Bridge |
| `invoices` | Section 5 — Payment Bridge |
| `tokbox_sessions` | Section 6 — Notification Bridge |
| `sms` | Section 6 — Notification Bridge |

---

## 4. Summary of Gaps and Discrepancies

| # | Issue | Source | Impact |
|---|---|---|---|
| 1 | `mco_slots_availability` row count is stale (7 vs 16) | Folder has newer data | Doc needs update |
| 2 | `mcoId` still NULL for all 16 rows | Folder confirms | Data quality bug — slot-to-MCO lookup broken |
| 3 | `booked_time` format undocumented (integer minutes) | Folder reveals | Any code converting this to a TIME type will break |
| 4 | `distance` / `eta` are strings not numbers | Folder reveals | Cannot use as DECIMAL in migration |
| 5 | `bookings_timeline` has `ON_ROUTE` and `ARRIVED` statuses | Folder reveals | Missing from doc's status list |
| 6 | `recurring_bookings.booked_date` has 2028 test dates | Folder reveals | Data quality flag |
| 7 | `mco_time_slots` fully undocumented in connections doc | Only in folder | FK target with no source documentation |
| 8 | `mcos` table columns undocumented | Only in folder | Core MCO entity with no column-level doc |
| 9 | `services` table columns undocumented | Only in folder | `mco_involved` and `sample_collection` flags drive connection logic |
