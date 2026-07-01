# MCO App — Missing Items

Extracted from `mco_app_gap_analysis.md`. Only missing columns, missing tables, and unconfigured data tables are listed here. Bugs and UI-only issues are excluded.

---

## Missing Columns

| # | Table | Missing Column(s) | Why It's Needed |
|---|---|---|---|
| 1 | `bookings` | `priority` | URGENT / NORMAL priority badge on service request cards — no schema backing |
| 2 | `bookings` | `note` | Pre-service clinical notes (e.g. "Patient has history of hypertension", "Fast 12 hours") shown on request cards |
| 3 | `bookings` | `decline_reason` | MCO can decline a service request — reason not storable; only patient `cancel_reason` exists |
| 4 | `bookings` | `actual_duration` | Service completion shows "45 min" actual time — only planned `service_time_in_minutes` is stored |
| 5 | `bookings` | `patient_consent` | Patient verbal consent checkbox for extra services added mid-visit — not persisted |
| 6 | `otps` | `type` | Same table serves login OTP (6-digit), service-start OTP (4-digit), and completion OTP (4-digit) — no way to distinguish |
| 7 | `otps` | `booking_id` | Service-start and completion OTPs cannot be linked to a specific booking for audit |
| 8 | `chat_messages` | `is_read` | "Mark all read" button and unread badge have no schema backing |
| 9 | `chat_messages` | `delivery_status` | Message delivery state (sent/delivered/read) not stored |
| 10 | `notifications` | `is_read` | "Mark all read" button and unread dot indicator have no schema backing |
| 11 | `notifications` | `read_at` | Timestamp for when a notification was read cannot be stored |
| 12 | `notifications` | `type` | Notification categories (Service Request, Inventory Alert, Sample Ready, Reminder, Rating) cannot be differentiated |

---

## Missing Tables

| # | Table | Why It's Needed |
|---|---|---|
| 1 | `device_readings` | MCO "Readings" tab captures vitals from connected devices (BP, SpO2, Blood Glucose) — no table to store them per booking |
| 2 | `booking_extra_services` | Extra services added during a home visit — `bookings.service_id` is a single FK and cannot store multiple services |
| 3 | `service_consumables_log` | "Consumables Used" during a service — `mco_inventory_items.no_of_units_used` is a running total; per-booking breakdown requires its own table |
| 4 | `checklist_completions` | Protocol checklist items (ticked per booking) — always shows "0/0 completed" because completion state is never saved |
| 5 | `break_schedule` | "Lunch Break" slots (12:00–1:00 PM) in Day schedule — recurring breaks have no schema |
| 6 | `blocked_slots` | Individual "Blocked" time slots in Day schedule — no table to flag specific slots per MCO per date |
| 7 | `mco_performance_snapshots` | Weekly performance metrics (+12%, +0.2 rating, +3% acceptance) require historical snapshots to compute week-over-week deltas |
| 8 | `mco_location_tracking` | MCO GPS coordinates captured while en route — ETA/distance stored once; no continuous trail for audit |
| 9 | `mco_recommendations` | MCO can recommend additional care ("Search & Recommend Consultation") — recommendations are not tracked |
| 10 | `payment_links` | "Send Payment Link via PayU WhatsApp/SMS" for extra service payment — generated links have no table |
| 11 | `payment_qr_codes` | "Scan QR Code" payment method for extra services — QR session data has no table |
| 12 | `quick_message_templates` | "Starting my journey now", "On my way!", "Arriving in 15 minutes" etc. are hardcoded — no table for admin-manageable templates |
| 13 | `pre_acceptance_verification_log` | MCO pre-acceptance inventory checklist completion (Face Masks ✓, Sanitizer ✓) is not persisted — progress % lost on close |
| 14 | `login_attempts` | MCO login audit trail — failed OTP attempts and successful logins not recorded |
| 15 | `inventory_alert_thresholds` | "Inventory Low Stock" notification (e.g. "Bandages running low") requires configurable thresholds per item |
| 16 | `mco_schedule_config` | `time_slots.csv` has 3 coarse rows; UI shows 30-min slots 8:00 AM–6:30 PM — the full slot grid has no schema |

---

## Unconfigured Data (Table Exists, No Useful Rows)

| # | Table | Issue |
|---|---|---|
| 1 | `slots_availability` | 7 rows total; `mcoId` is NULL for all — no MCO-specific slot availability is configured |
| 2 | `mco_inventory_items` | 2 rows, both for `mco_id = 1` — MCO "sam s" has no inventory assigned; "Add Consumables" always shows empty |
| 3 | `mco_reviews` | 3 rows only — too few to compute meaningful performance metrics; "Average Rating: 4" and "Acceptance Rate: 12.50%" are not statistically valid |

---

## Summary

| Category | Count |
|---|---:|
| Missing columns | 12 |
| Missing tables | 16 |
| Unconfigured data tables | 3 |
| **Total** | **31** |
