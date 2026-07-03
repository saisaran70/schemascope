# Patient App — Missing Items

Extracted from `patient_app_gap_analysis.md`. Only missing columns, missing tables, and empty tables. Bugs and design issues excluded.

---

## Missing Columns

| # | Table | Missing Column(s) | Why It's Needed |
|---|---|---|---|
| 1 | `addresses` | `receiver_name`, `receiver_phone` | "Receiver Details" form fields collected in UI but no columns to store them |
| 2 | `patients` | `is_phone_verified` | "Verified ✓" badge next to phone number has no backing |
| 3 | `patients` | `uhid` | UHID (SIMS-PT-000049) shown in invoices but not stored in patient record |
| 4 | `family_members` | `mobile` | No way to store or contact a family member directly |
| 5 | `health_records` | `title`, `description` | Documents have no human-readable name — only URL stored |
| 6 | `patient_referred` | `earned_amount`, `pending_payout`, `status` | "₹250 Earned · 2 Pending" referral rewards have nowhere to be stored |
| 7 | `callback_requests` | `reason`, `status`, `priority`, `assigned_to`, `scheduled_time`, `resolved_at` | Table has only 2 columns (`patient_id`, `created_at`) — Report Issue / Request Callback feature is non-functional |
| 8 | `offers` | `image` | Offer/coupon cards cannot show banner images |
| 9 | `doctors` | `about`, `bio` | Doctor "About" section on profile has no backing column |
| 10 | `doctors` | `clinic_name`, `clinic_city` | "Practice Location: SIMS, Hyderabad" has no backing columns |
| 11 | `doctors` | `is_verified` | "Verified" badge on doctor profile has no backing |
| 12 | `doctors` | `second_opinion_fee` | 2nd Opinion fee shown separately in UI but no dedicated column |
| 13 | `bookings` | `queue_position` | "Queue: 2 ahead" shown on home and insta consult screens |
| 14 | `tokbox_sessions` | `call_duration` | Call duration shown during video call but never persisted |

---

## Missing Tables

| # | Table | Why It's Needed |
|---|---|---|
| 1 | `hospitals` | "Visit Our Hospital" card (Ozone Hospitals, 4.7 ★, Kothapet) is fully hardcoded — no schema |
| 2 | `faqs` | Help & Support FAQ content is hardcoded — cannot be managed via admin |
| 3 | `issue_reports` | "Report an Issue" submission form has nowhere to write |
| 4 | `search_history` | "Recent Searches" chips cannot persist per-patient |
| 5 | `trending_searches` | "Trending Searches" chips (Diabetes checkup, Dermatologist…) are hardcoded |
| 6 | `ai_sessions` / `ai_queries` | "Find Specialist AI" and AI Health Assistant have zero schema backing |
| 7 | `cart` / `booking_cart` | Multi-service cart in Homecare is ephemeral — no persistence |
| 8 | `booking_items` | `bookings.service_id` is a single FK — no schema for multi-service bookings |
| 9 | `legal_documents` | T&C, Privacy Policy, Disclaimer, Data Security, About Us — all hardcoded |
| 10 | `support_contacts` | Support phone numbers and operating hours are hardcoded |
| 11 | `referral_wallet` / `referral_transactions` | Referral earnings, payouts, and pending rewards have no table |

---

## Empty Tables

| # | Table | UI Feature Affected |
|---|---|---|
| 1 | `reviews.csv` | Doctor ratings ("98% Satisfied", ★5 ratings) are all fabricated — no real data |
| 2 | `doctor_achivements.csv` | Achievements section on doctor profile is always empty (also has spelling typo: "achivements") |

---

## Summary

| Category | Count |
|---|---:|
| Missing columns | 14 |
| Missing tables | 11 |
| Empty tables | 2 |
| **Total** | **27** |
