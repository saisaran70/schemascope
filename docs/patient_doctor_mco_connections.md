# Patient ↔ Doctor ↔ MCO Connection Tables — Med360

Tables that bridge the Patient app, Doctor app, and MCO (home-care) app.

---

## How the Apps Connect

```
patients ──────────────────────────────────────────────────────────┐
   │                                                               │
   │  books via bookings                                           │
   ▼                                                               │
bookings ─── doctor_id ──► doctors (Doctor app)                    │
    │                                                              │
    └─── mco_id + service_id ──► mcos + services (MCO app)        │
                                                                   │
payments ◄─── patient_id ────────────────────────────────────────── ┘
```

`bookings` is the **central hub** — every consultation, home-care visit, and second opinion flows through it.

---

## Section 1 — The Central Hub

### `bookings` — 1,025 rows
*(sims_med360_booking)*

Single table that connects patient, doctor, MCO, and service in one record.

| Column | Connects To |
|---|---|
| `id` | PK |
| `patient_id` | → `patients.id` (Patient app) |
| `family_member_id` | → `family_members.id` (Patient app) |
| `doctor_id` | → `doctors.id` (Doctor app) |
| `mco_id` | → `mcos.id` (MCO app) |
| `service_id` | → `services.id` (MCO app) |
| `address_id` | → `addresses.id` (Patient app) |
| `specialist_id` | Specialist doctor reference |
| `type` | VIDEO / IN_PERSON / HOME_CARE_SERVICE |
| `status` | PENDING / IN_PROGRESS / COMPLETED / CANCELLED |
| `booked_date` | |
| `booked_time` | |
| `amount` / `price` / `discount` / `gst` / `service_charge` | Financial summary |
| `is_second_opinion` | Boolean — doctor second opinion flow |
| `is_recurring` | Boolean — links to `recurring_bookings` |
| `sample_required` | Boolean — triggers MCO sample collection flow |
| `prescription_generated` | Boolean |
| `report_generated` | Boolean |
| `cancelled_by` / `cancel_reason` | |
| `reschedule_count` / `rescheduled_date` / `rescheduled_time` | |
| `clinical_notes` / `description` | |
| `distance` / `eta` | MCO home visit logistics |
| `created_at` / `updated_at` | |

### `bookings_timeline` — 3,763 rows
*(sims_med360_booking)*

Audit trail of every status change on a booking (used by all three apps).

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `status` | Snapshot of status at each transition |
| `created_at` | |

### `recurring_bookings` — 6 rows
*(sims_med360_booking)*

Scheduled repeat visits generated from a parent booking.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` (parent) |
| `booked_date` | |
| `booked_time` | |
| `created_at` / `updated_at` | |

---

## Section 2 — Patient ↔ Doctor Tables

### `prescriptions` — 30 rows
*(sims_med360_booking)*

Doctor writes a prescription for a patient through a booking.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `patient_id` | → `patients.id` (Patient app) |
| `doctor_id` | → `doctors.id` (Doctor app) |
| `known_allergies` | |
| `medical_history` | |
| `diagnosis` | |
| `instructions` | |
| `active` | Boolean (0/1) |
| `created_at` / `updated_at` | |

### `medications` — 30 rows
*(sims_med360_booking)*

Individual medicine line items on a doctor's prescription.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `prescription_id` | → `prescriptions.id` |
| `patient_id` | → `patients.id` (Patient app) |
| `doctor_id` | → `doctors.id` (Doctor app) |
| `drug_name` | |
| `dose_strength` / `dosage_form` | |
| `route` / `timing` / `frequency` / `duration` | |
| `notes` | |
| `created_at` / `updated_at` | |

### `medical_histories` — 11 rows
*(sims_med360_booking)*

Patient's health background captured during a booking consultation.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `patient_id` | → `patients.id` (Patient app) |
| `known_allergies` | |
| `chronic_conditions` | |
| `current_medications` | |
| `recent_surgeries` | |
| `created_at` / `updated_at` | |

### `patient_referred` — 16 rows
*(sims_med360_booking)*

Doctor refers a patient to another service or specialization.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `patient_id` | → `patients.id` (Patient app) |
| `service_id` | → `services.id` (MCO app — original service) |
| `referred_service_id` | → `services.id` (MCO app — referred service) |
| `referred_specialization_id` | → `specializations.id` (Doctor app) |
| `referred_by` | Name of referring doctor |
| `referrer_id` | → `doctors.id` (Doctor app) |
| `referring_date` / `referring_time` | |
| `referral_reason` / `urgency_level` | |
| `frequency` / `no_of_sessions` | |
| `service_type` | |
| `created_at` / `updated_at` | |

### `recommendations` — 42 rows
*(sims_med360_booking)*

Doctor recommends follow-up services or specialists to a patient after a booking.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `patient_id` | → `patients.id` (Patient app) |
| `family_member_id` | → `family_members.id` (Patient app) |
| `service_id` | → `services.id` (MCO app — current service) |
| `recommended_service_id` | → `services.id` (MCO app — recommended) |
| `recommended_specialization_id` | → `specializations.id` (Doctor app) |
| `recommended_by` | Name of recommending doctor |
| `referrer_id` | → `doctors.id` (Doctor app) |
| `referral_reason` / `urgency_level` | |
| `recommend_date` / `recommend_time` | |
| `no_of_sessions` / `frequency` | |
| `type` / `service_type` | |
| `created_at` / `updated_at` | |

### `doctor_slots_availability` — 21 rows
*(sims_med360_doctor)*

Doctor's available time slots that the patient app uses for appointment booking.

| Column | Connects To |
|---|---|
| `id` | PK |
| `doctor_id` | → `doctors.id` (Doctor app) |
| `date` | |
| `time_slot_id` | → `time_slots.id` (Doctor app) |
| `booked` | Boolean — set when patient books |

### `reviews` — 0 rows *(empty)*
*(sims_med360_doctor)*

Intended for patient ratings and text reviews of doctors. Currently unpopulated.

---

## Section 3 — Patient ↔ MCO Tables

### `mco_reviews` — 3 rows
*(sims_med360_mco)*

Patient's rating and review for an MCO service after a completed booking.

| Column | Connects To |
|---|---|
| `id` | PK |
| `mco_id` | → `mcos.id` (MCO app) |
| `patient_id` | → `patients.id` (Patient app) |
| `booking_id` | → `bookings.id` |
| `service_id` | → `services.id` (MCO app) |
| `rating` | Numeric |
| `review` | Text |
| `active` | Boolean (0/1) |
| `created_at` / `updated_at` | |

### `mco_services` — 44 rows
*(sims_med360_mco)*

Defines which services each MCO offers — patient app queries this to show available providers.

| Column | Connects To |
|---|---|
| `id` | PK |
| `mco_id` | → `mcos.id` (MCO app) |
| `service_id` | → `services.id` (MCO app) |
| `active` | Boolean (0/1) |
| `created_at` / `updated_at` | |

### `mco_slots_availability` — 7 rows
*(sims_med360_mco)*

Service time slots exposed to the patient app for booking MCO home-care visits.
> ⚠️ Known issue: `mcoId` is NULL for all 7 rows — MCO FK data is missing.

| Column | Connects To |
|---|---|
| `id` | PK |
| `service_id` | → `services.id` (MCO app) |
| `mcoId` | → `mcos.id` (MCO app) — currently NULL |
| `date` | |
| `time_slot_id` | → `time_slots.id` (MCO app) |
| `no_of_slots` | Available capacity |
| `active` | Boolean (0/1) |

### `patient_samples` — 31 rows
*(sims_med360_booking)*

Lab samples collected by an MCO nurse during a home-care visit.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `patient_id` | → `patients.id` (Patient app) |
| `sample_type_id` | → `sample_types.id` |
| `container_type_id` | → `container_types.id` |
| `quantity` | |
| `status` | Collection status |
| `barcode` | |
| `storage_condition` | |
| `notes` | |
| `created_at` / `updated_at` | |

### `patient_sample_notes` — 43 rows
*(sims_med360_booking)*

MCO nurse status notes as sample moves through collection → storage → lab.

| Column | Connects To |
|---|---|
| `id` | PK |
| `sample_id` | → `patient_samples.id` |
| `notes` | |
| `previous_status` | |
| `current_status` | |
| `created_at` / `updated_at` | |

---

## Section 4 — Shared Documents

### `documents` — 78 rows
*(sims_med360_booking)*

Files uploaded at any stage of a booking — by patient, doctor, or MCO nurse.

| Column | Connects To |
|---|---|
| `id` | PK |
| `booking_id` | → `bookings.id` |
| `patientSampleId` | → `patient_samples.id` (nullable) |
| `type` | Document category |
| `document` | File path / URL |
| `name` | Original filename |
| `size` | File size |
| `uploaded_by` | Actor who uploaded |
| `created_at` | |

---

## Section 5 — Payment Bridge

### `payments` — 282 rows
*(sims_med360_payment)*

Payment transaction initiated by patient for a booking.

| Column | Connects To |
|---|---|
| `id` | PK |
| `patient_id` | → `patients.id` (Patient app) |
| `service_amount` / `paid_amount` / `discount` / `gst` / `gst_amount` | |
| `coupon_code` / `coupon_discount` | |
| `payment_gateway` / `payment_gateway_id` / `gateway_amount` / `gateway_response` | |
| `payment_type` / `status` | |
| `initiator` / `initiator_id` | Who triggered the payment |
| `created_at` / `updated_at` | |

### `payment_bookings` — 331 rows
*(sims_med360_payment)*

Join table linking payments to bookings (one payment can cover one booking).

| Column | Connects To |
|---|---|
| `id` | PK |
| `payment_id` | → `payments.id` |
| `booking_id` | → `bookings.id` |
| `created_at` | |

### `invoices` — 16 rows
*(sims_med360_payment)*

Tax invoice generated after a booking is completed and paid.

| Column | Connects To |
|---|---|
| `id` | PK |
| `invoice_number` | |
| `payment_id` | → `payments.id` |
| `booking_id` | → `bookings.id` |
| `patient_id` | → `patients.id` (Patient app) |
| `patient_name` / `patient_phone` / `patient_email` / `patient_uhid` / `patient_address` | Denormalized snapshot |
| `provider_name` | Doctor or MCO name (denormalized) |
| `service_name` / `service_type` / `service_subtitle` | |
| `sac_code` | GST SAC code |
| `base_amount` / `discount` / `gst_percent` / `total` | |
| `transaction_id` / `payment_method` / `upi_id` | |
| `date` / `created_at` | |

---

## Section 6 — Notification Bridge

### `tokbox_sessions` — 274 rows
*(sims_med360_notifications — MongoDB)*

Video call sessions between patient and doctor, linked via `bookingId`.

| Column | Notes |
|---|---|
| `_id` | MongoDB ObjectId |
| `bookingId` | → `bookings.id` |
| `sessionId` | OpenTok/TokBox session token |
| `name` | Session label |

### `sms` — 673 rows
*(sims_med360_notifications — MongoDB)*

SMS messages sent to users at booking events; `bookingId` and `mcoId` tie messages to context.

| Column | Notes |
|---|---|
| `_id` | MongoDB ObjectId |
| `userId` | → `users._id` (auth) |
| `bookingId` | → `bookings.id` |
| `mcoId` | → `mcos.id` (MCO app) |
| `mobile` | |
| `type` / `message` / `smsResponse` | |
| `otp` / `variablesValues` | |
| `createdAt` | |

---

## Full Summary

| Table | Module | Patient | Doctor | MCO | Rows |
|---|---|:---:|:---:|:---:|---:|
| `bookings` | booking | ✓ | ✓ | ✓ | 1,025 |
| `bookings_timeline` | booking | — | — | — | 3,763 |
| `recurring_bookings` | booking | — | — | — | 6 |
| `prescriptions` | booking | ✓ | ✓ | — | 30 |
| `medications` | booking | ✓ | ✓ | — | 30 |
| `medical_histories` | booking | ✓ | — | — | 11 |
| `patient_referred` | booking | ✓ | ✓ | ✓ | 16 |
| `recommendations` | booking | ✓ | ✓ | ✓ | 42 |
| `documents` | booking | ✓ | ✓ | ✓ | 78 |
| `patient_samples` | booking | ✓ | — | ✓ | 31 |
| `patient_sample_notes` | booking | — | — | ✓ | 43 |
| `doctor_slots_availability` | doctor | ✓ | ✓ | — | 21 |
| `reviews` *(empty)* | doctor | ✓ | ✓ | — | 0 |
| `mco_reviews` | mco | ✓ | — | ✓ | 3 |
| `mco_services` | mco | ✓ | — | ✓ | 44 |
| `mco_slots_availability` | mco | ✓ | — | ✓ | 7 |
| `payments` | payment | ✓ | — | — | 282 |
| `payment_bookings` | payment | — | — | — | 331 |
| `invoices` | payment | ✓ | — | — | 16 |
| `tokbox_sessions` | notifications | ✓ | ✓ | — | 274 |
| `sms` | notifications | ✓ | — | ✓ | 673 |
| **Total** | | | | | **6,722** |
