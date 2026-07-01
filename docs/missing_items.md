# Med360 — Missing Items

Extracted from `doctor_app_gap_analysis.md`. Only missing columns, missing tables, and empty tables are listed here. Bugs and schema design issues are excluded.

---

## Missing Columns

| # | Table | Missing Column(s) | Why It's Needed |
|---|---|---|---|
| 1 | `bookings` | `token_number` | Token-604, Token-608 etc. shown in UI but no column backs it |
| 2 | `bookings` | `queue_sub_status` | "Ready", "Pending", "Next" queue badges have no backing |
| 3 | `bookings` | `call_mode` | "Voice" badge on in-progress cards has no backing |
| 4 | `prescriptions` | `follow_up_scheduled`, `follow_up_date` | "Schedule Follow-up" checkbox result is not persistable |
| 5 | `doctors` | `is_verified` | "Verified" badge on profile has no backing |
| 6 | `doctors` | `managed_by_admin` | "Profile managed by admin" label has no backing |
| 7 | `doctors` | `doctor_type` | "Specialist (Appointment-based)" label has no backing — `category` is overloaded |
| 8 | `tokbox_sessions` | `call_start_time`, `call_end_time`, `call_duration` | Call duration counter shown in video screen is never persisted |
| 9 | `notifications` | `is_read`, `read_at` | "Unread" tab is not backable without a read-state column |
| 10 | `notifications` | `is_cleared` / `cleared_at` | "Clear All" button has nowhere to write |
| 11 | `notifications` | `type` / `category` | All notifications are in a single bucket with no categorization |
| 12 | `health_records` | `report_date` | Only upload timestamp exists; actual report date is not stored |
| 13 | `doctors` | `review_count` | Ratings shown in UI need a count alongside the score |

---

## Missing Tables

| # | Table | Why It's Needed |
|---|---|---|
| 1 | `vitals` (structured) | MedTel report shows BP, Sugar, Temp, BMI — all stored only as PDF blob, not queryable |
| 2 | `date_range_availability` | "Date Range" scheduling mode in Manage Availability has no schema backing |
| 3 | `weekly_schedule` / `recurring_slots` | No way to define "every Monday 9am–5pm" — schema only stores individual date rows |
| 4 | `learning_resources` | "Learning Resources" link in Profile & Settings has no data source |

---

## Empty Tables (exist but have 0 rows)

| # | Table | UI Feature Broken |
|---|---|---|
| 1 | `templates.csv` | Prescription Quick Templates — "Basics" and "Save" chips appear hardcoded; Browse All is non-functional |
| 2 | `reviews.csv` | Doctor ratings and feedback — rating shows 0 ★, 0 ratings everywhere |
| 3 | `doctor_achivements.csv` | Achievements section — completely empty (also has a spelling typo: "achivements") |

---

## Summary

| Category | Count |
|---|---:|
| Missing columns | 13 |
| Missing tables | 4 |
| Empty tables | 3 |
| **Total** | **20** |
