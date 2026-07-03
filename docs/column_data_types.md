# Med360 Column Data Types Reference

> **Legend — MySQL Type column**
> - `INT UNSIGNED` / `TINYINT(1)` / `DECIMAL` / `VARCHAR` / `TEXT` / `DATETIME` / `DATE` / `TIME` / `JSON` / `ENUM(...)` — target MySQL column type for each column in the platform schema

---

## Module: sims_med360_auth

### otps *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| userId | VARCHAR(36) | FK → users._id (UUID) |
| otp | VARCHAR(255) | OTP value |
| createdAt | DATETIME | |
| expiresAt | DATETIME | |

### users *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| email | VARCHAR(255) | |
| password | VARCHAR(255) | bcrypt hash |
| confirmPassword | VARCHAR(255) | |
| role | ENUM('admin','doctor','mco','patient') | values seen in data |
| lastLogin | DATETIME | |
| userId | VARCHAR(36) | UUID, FK → internal user profile |
| createdAt | DATETIME | |
| active | TINYINT(1) | boolean (true/false stored as text) |
| mobile | VARCHAR(20) | |
| deviceId | VARCHAR(255) | |
| fcmToken | VARCHAR(500) | FCM push token |

---

## Module: sims_med360_patient

### addresses
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| family_member_id | INT UNSIGNED | FK → family_members.id; nullable |
| address1 | VARCHAR(255) | |
| address2 | VARCHAR(255) | nullable |
| landmark | VARCHAR(255) | |
| city | VARCHAR(255) | |
| type | ENUM('HOME','WORK','OTHER') | values seen: HOME, WORK |
| pin_code | VARCHAR(20) | stored as text to preserve leading zeros |
| state_id | INT UNSIGNED | FK → states.id |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| is_primary | TINYINT(1) | 0/1 |
| latitude | DECIMAL(10,6) | |
| longitude | DECIMAL(10,6) | |
| active | TINYINT(1) | 0/1 |

### banners
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| title | VARCHAR(255) | |
| description | TEXT | |
| type | ENUM('TEXT','IMAGE') | values seen: TEXT, IMAGE |
| badge | VARCHAR(100) | nullable |
| image | VARCHAR(500) | URL; nullable |
| active | TINYINT(1) | 0/1 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### callback_requests
| Column | MySQL Type | Notes |
|---|---|---|
| patient_id | INT UNSIGNED | FK → patients.id |
| created_at | DATETIME | |

### family_members
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| relation | ENUM('FATHER','MOTHER','SPOUSE','BROTHER','SISTER','CHILD','OTHER') | values seen: FATHER, BROTHER |
| name | VARCHAR(255) | |
| age | INT | |
| gender | ENUM('M','F','O') | values seen: M, F |
| blood_group | VARCHAR(10) | e.g. O+, AB- |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| profile_pic | VARCHAR(500) | URL; nullable |
| active | TINYINT(1) | 0/1 |

### health_records
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| family_memeber_id | INT UNSIGNED | FK → family_members.id; nullable (note typo in column name — preserve) |
| type | ENUM('PRESCRIPTION','REPORT','LAB_RESULT','OTHER') | values seen: PRESCRIPTION |
| document | VARCHAR(500) | URL |
| size | VARCHAR(50) | stored as "60.58 KB" — free text |
| created_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### industries
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### offers
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| title | VARCHAR(255) | |
| description | TEXT | |
| expiry_date | DATE | |
| minimum_order | INT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| code | VARCHAR(100) | |
| discount | DECIMAL(10,2) | stored as text |
| discount_type | ENUM('PERCENTAGE','FLAT') | values seen: PERCENTAGE |
| active | TINYINT(1) | 0/1 |

### patients
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| user_map_id | VARCHAR(36) | UUID; FK → users.userId |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| last_login | DATETIME | |
| blood_group | VARCHAR(10) | e.g. B+, O- |
| dob | DATE | |
| email | VARCHAR(255) | |
| employment_status | ENUM('WORKING','STUDENT','UNEMPLOYED','RETIRED','OTHER') | values seen: WORKING |
| first_name | VARCHAR(255) | |
| gender | ENUM('M','F','O') | values seen: M, F |
| last_name | VARCHAR(255) | |
| occupation | VARCHAR(255) | |
| status | VARCHAR(255) | empty in most rows; use VARCHAR |
| emergency_contact_name | VARCHAR(255) | |
| emergency_contact_number | VARCHAR(20) | |
| mobile | VARCHAR(20) | |
| industry_id | INT UNSIGNED | FK → industries.id |
| profile_pic | VARCHAR(500) | URL; nullable |
| referral_code | VARCHAR(100) | |
| active | TINYINT(1) | 0/1 |

### settings (patient)
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| push_notification | TINYINT(1) | 0/1 |
| email_notification | TINYINT(1) | 0/1 |
| sms_notification | TINYINT(1) | 0/1 |
| booking_reminders | TINYINT(1) | 0/1 |
| promotional_offers | TINYINT(1) | 0/1 |
| dark_mode | TINYINT(1) | 0/1 |
| language | ENUM('ENGLISH','HINDI','TELUGU') | values seen: ENGLISH |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### states
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### hospitals
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | e.g. Ozone Hospitals |
| address | TEXT | |
| city | VARCHAR(255) | |
| rating | DECIMAL(3,2) | |
| image | VARCHAR(500) | URL; nullable |
| phone | VARCHAR(20) | |
| active | TINYINT(1) | 0/1 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### issue_reports
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| booking_id | INT UNSIGNED | FK → bookings.id; nullable |
| reason | TEXT | |
| status | ENUM('OPEN','IN_REVIEW','RESOLVED','CLOSED') | |
| priority | ENUM('LOW','MEDIUM','HIGH','URGENT') | |
| assigned_to | INT UNSIGNED | admin user id; nullable |
| scheduled_time | DATETIME | nullable |
| resolved_at | DATETIME | nullable |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### ai_sessions
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| session_type | ENUM('FIND_SPECIALIST','HEALTH_ASSISTANT') | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### ai_queries
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| session_id | INT UNSIGNED | FK → ai_sessions.id |
| query | TEXT | patient question |
| response | TEXT | AI response |
| created_at | DATETIME | |

### cart
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| service_id | INT UNSIGNED | FK → services.id |
| quantity | INT | |
| created_at | DATETIME | |

### referral_transactions
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| coupon_id | INT UNSIGNED | FK → coupons; nullable |
| patient_id | INT UNSIGNED | FK → patients.id |
| referred_patient_id | INT UNSIGNED | FK → patients.id; nullable |
| discount | DECIMAL(10,2) | referral discount value |
| type | ENUM('EARNED','REDEEMED','PENDING','EXPIRED') | |
| status | ENUM('PENDING','COMPLETED','FAILED') | |
| created_at | DATETIME | |

---

## Module: sims_med360_doctor

### categories
> *File exists but is empty (header only — no columns detected)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### colleges
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| city | VARCHAR(255) | |
| active | TINYINT(1) | 0/1 |

### custom_time_slots
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| date | DATE | |
| start_min | INT | minutes from midnight |
| end_min | INT | minutes from midnight |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| available | TINYINT(1) | 0/1 |

### doctors
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| last_login | DATETIME | |
| user_map_id | VARCHAR(36) | UUID; FK → users.userId |
| aadhar_number | VARCHAR(20) | |
| category | VARCHAR(50) | stored as "0" in sample; keep VARCHAR |
| city | VARCHAR(255) | |
| dob | DATE | |
| email | VARCHAR(255) | |
| experience | INT | years of experience |
| first_name | VARCHAR(255) | |
| gender | ENUM('M','F','O') | values seen: M, F |
| last_name | VARCHAR(255) | |
| registration_number | VARCHAR(100) | |
| available | TINYINT(1) | 0/1 |
| insta_consultation | TINYINT(1) | 0/1 |
| about | TEXT | |
| consultation_fee | DECIMAL(10,2) | |
| hospital | VARCHAR(255) | |
| insta_consultation_fee | DECIMAL(10,2) | |
| location | VARCHAR(255) | |
| modes | VARCHAR(100) | comma-separated: VIDEO, CLINIC |
| rating | DECIMAL(3,2) | |
| second_opinion | TINYINT(1) | 0/1 |
| second_opinion_fee | DECIMAL(10,2) | |
| mobile | VARCHAR(20) | |
| profile_pic | VARCHAR(500) | URL; nullable |
| signature | VARCHAR(500) | URL; nullable |
| clinic_address_1 | VARCHAR(255) | nullable |
| clinic_address_2 | VARCHAR(255) | nullable |
| clinic_name | VARCHAR(255) | nullable |

### doctor_achivements *(filename typo — preserved)*
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| title | VARCHAR(255) | e.g. 500+ Consultations |
| description | TEXT | nullable |
| icon | VARCHAR(500) | URL to badge/icon; nullable |
| active | TINYINT(1) | 0/1 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### doctor_expertise
| Column | MySQL Type | Notes |
|---|---|---|
| doctor_id | INT UNSIGNED | FK → doctors.id |
| expertise_id | INT UNSIGNED | FK → expertise.id |

### doctor_languages
| Column | MySQL Type | Notes |
|---|---|---|
| doctor_id | INT UNSIGNED | FK → doctors.id |
| language_id | INT UNSIGNED | FK → languages.id |

### doctor_qualifications
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| qualification_id | INT UNSIGNED | FK → qualifications.id |
| created_at | DATETIME | |
| college_id | INT UNSIGNED | FK → colleges.id |

### doctor_specializations
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| specialization_id | INT UNSIGNED | FK → specializations.id |
| created_at | DATETIME | |

### doctor_test
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### expertise
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| active | TINYINT(1) | 0/1 |

### insta_consultaion_documents *(filename typo — preserved)*
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### insta_consultation_requests
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### languages
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### qualifications
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| active | TINYINT(1) | 0/1 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### reviews (doctor)
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| booking_id | INT UNSIGNED | FK → bookings.id |
| rating | DECIMAL(2,1) | e.g. 4.5 |
| review | TEXT | free-text feedback |
| active | TINYINT(1) | 0/1 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### slots_availability (doctor)
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| date | DATE | |
| time_slot_id | INT UNSIGNED | FK → time_slots.id |
| booked | TINYINT(1) | 0/1 |

### specializations
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| active | TINYINT(1) | 0/1 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### time_slots (doctor)
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| end_min | INT | minutes from midnight |
| start_min | INT | minutes from midnight |

---

## Module: sims_med360_mco

### checklists
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| description | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### inventory_items
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| category | VARCHAR(100) | e.g. PPE |
| unitType | ENUM('PIECES','PAIRS','UNITS','BOTTLES','BOXES') | values seen: PIECES, PAIRS, UNITS |
| no_of_units | INT | |
| restocked_at | DATETIME | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### inventory_item_requests
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| mco_id | INT UNSIGNED | FK → mcos.id |
| inventory_item_id | INT UNSIGNED | FK → inventory_items.id |
| no_of_units | INT | |
| reason | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### mcos
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| user_map_id | VARCHAR(36) | UUID; FK → users.userId |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| last_login | DATETIME | |
| aadhar_number | VARCHAR(20) | |
| dob | DATE | |
| email | VARCHAR(255) | |
| experience | INT | years |
| first_name | VARCHAR(255) | |
| gender | ENUM('M','F','O') | values seen: M, F |
| last_name | VARCHAR(255) | |
| location | VARCHAR(255) | |
| rating | DECIMAL(3,2) | |
| registration_number | VARCHAR(100) | |
| status | ENUM('online','offline') | values seen: online, offline |
| specialization | VARCHAR(255) | nullable |
| mobile | VARCHAR(20) | |
| profile_pic | VARCHAR(500) | URL; nullable |

### mco_inventory_items
| Column | MySQL Type | Notes |
|---|---|---|
| mco_id | INT UNSIGNED | FK → mcos.id |
| inventory_item_id | INT UNSIGNED | FK → inventory_items.id |
| no_of_units | INT | |
| restocked_at | DATETIME | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| no_of_units_used | INT | |

### mco_products
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### mco_reviews
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| mco_id | INT UNSIGNED | FK → mcos.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| booking_id | INT UNSIGNED | FK → bookings.id |
| service_id | INT UNSIGNED | FK → services.id |
| rating | DECIMAL(3,2) | stored as "4.00" |
| review | TEXT | |
| created_at | DATETIME | |
| active | TINYINT(1) | 0/1 |
| updated_at | DATETIME | |

### mco_services
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| mco_id | INT UNSIGNED | FK → mcos.id |
| service_id | INT UNSIGNED | FK → services.id |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### popular_services
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### products
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### protocols
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| description | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### requirements
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| description | TEXT | |
| type | ENUM('GENERAL','SPECIFIC') | values seen: GENERAL |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### services
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| description | TEXT | |
| service_type_id | INT UNSIGNED | FK → service_types.id |
| service_category_id | INT UNSIGNED | FK → service_categories.id |
| price | DECIMAL(10,2) | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| service_time_in_minutes | INT | |
| tag | VARCHAR(100) | nullable |
| bookings | INT | total booking count |
| rating | DECIMAL(3,2) | |
| available | TINYINT(1) | 0/1 |
| mco_involved | TINYINT(1) | 0/1 |
| sample_collection | TINYINT(1) | 0/1 |
| type | ENUM('diagnostic','routine','emergency','preventive','critical') | values seen: diagnostic, routine, emergency, preventive, critical |
| duration | VARCHAR(100) | nullable |
| icon | VARCHAR(500) | URL; nullable |
| reviews | INT | nullable |
| active | TINYINT(1) | 0/1 |

### services_ratings
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### service_categories
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| description | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| multipleBookings | TINYINT(1) | 0/1 |
| active | TINYINT(1) | 0/1 |

### service_checklists
| Column | MySQL Type | Notes |
|---|---|---|
| service_id | INT UNSIGNED | FK → services.id |
| checklist_id | INT UNSIGNED | FK → checklists.id |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### service_inventory_items
| Column | MySQL Type | Notes |
|---|---|---|
| service_id | INT UNSIGNED | FK → services.id |
| inventory_item_id | INT UNSIGNED | FK → inventory_items.id |
| no_of_units | INT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### service_products
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### service_protocols
| Column | MySQL Type | Notes |
|---|---|---|
| service_id | INT UNSIGNED | FK → services.id |
| protocol_id | INT UNSIGNED | FK → protocols.id |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### service_required_items
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### service_requirements
| Column | MySQL Type | Notes |
|---|---|---|
| service_id | INT UNSIGNED | FK → services.id |
| requirement_id | INT UNSIGNED | FK → requirements.id |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### service_reviews
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### service_tests
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### service_types
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| description | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| tag | ENUM('POPULAR','NULL') | values seen: POPULAR, NULL |
| service_category_id | INT UNSIGNED | FK → service_categories.id |
| active | TINYINT(1) | 0/1 |

### slots_availability (mco)
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| service_id | INT UNSIGNED | FK → services.id |
| date | DATE | |
| time_slot_id | INT UNSIGNED | FK → mco_time_slots.id |
| no_of_slots | INT | |
| mcoId | INT UNSIGNED | FK → mcos.id; currently NULL for all 16 rows — known data quality issue |
| active | TINYINT(1) | 0/1 |

### tests (mco)
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### time_slots (mco)
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| start_min | INT | minutes from midnight |
| end_min | INT | minutes from midnight |
| active | TINYINT(1) | 0/1 |

### top_services
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### trending_services
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| service_id | INT UNSIGNED | FK → services.id |
| category | ENUM('MOST_BOOKED','TOP_RATED','POPULAR') | values seen: MOST_BOOKED, TOP_RATED, POPULAR |

---

## Module: sims_med360_booking

### bookings
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| family_member_id | INT UNSIGNED | FK → family_members.id; nullable |
| requested_for | ENUM('OWN','FAMILY_MEMBER') | values seen: OWN, FAMILY_MEMBER |
| requested_time | DATETIME | |
| status | ENUM('PENDING','IN_PROGRESS','ON_ROUTE','ARRIVED','COMPLETED','CANCELLED') | values seen: COMPLETED, IN_PROGRESS, ON_ROUTE, ARRIVED |
| doctor_id | INT UNSIGNED | FK → doctors.id; nullable |
| cancelled_by | VARCHAR(50) | nullable |
| cancel_reason | TEXT | nullable |
| expiry_time | DATETIME | nullable |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| description | TEXT | nullable |
| service_id | INT UNSIGNED | FK → services.id |
| specialist_id | INT UNSIGNED | FK → doctors.id; nullable |
| type | ENUM('HOME_CARE_SERVICE','SPECIALIST_CONSULTATION','INSTA_CONSULTATION') | values seen: HOME_CARE_SERVICE |
| booked_date | DATE | |
| booked_time | INT | stored as minutes from midnight |
| mco_id | INT UNSIGNED | FK → mcos.id |
| address_id | INT UNSIGNED | FK → addresses.id |
| is_second_opinion | TINYINT(1) | 0/1 |
| sample_required | TINYINT(1) | 0/1 |
| clinical_notes | TEXT | nullable |
| distance | VARCHAR(50) | stored as "11.77 km"; use VARCHAR |
| eta | VARCHAR(50) | stored as "18 min"; use VARCHAR |
| amount | DECIMAL(10,2) | |
| discount | DECIMAL(10,2) | |
| is_recurring | TINYINT(1) | 0/1 |
| is_rescheduled | TINYINT(1) | 0/1 |
| price | DECIMAL(10,2) | |
| rescheduled_date | DATE | nullable |
| rescheduled_time | INT | nullable; minutes from midnight |
| gst | DECIMAL(10,2) | |
| service_charge | DECIMAL(10,2) | |
| prescription_generated | TINYINT(1) | 0/1 |
| report_generated | TINYINT(1) | 0/1 |
| reschedule_count | INT | |

### bookings_timeline
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| status | ENUM('PENDING','IN_PROGRESS','ON_ROUTE','ARRIVED','COMPLETED','CANCELLED') | values seen: ON_ROUTE, ARRIVED, IN_PROGRESS, COMPLETED |
| created_at | DATETIME | |

### container_types
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### documents
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| type | ENUM('CBC_REPORT','PRESCRIPTION','LAB_RESULT','OTHER') | values seen: CBC_REPORT, PRESCRIPTION |
| document | VARCHAR(500) | URL |
| patientSampleId | INT UNSIGNED | FK → patient_samples.id; nullable (camelCase preserved) |
| name | VARCHAR(255) | nullable |
| size | VARCHAR(50) | nullable; free text e.g. "2.5 MB" |
| created_at | DATETIME | |
| uploaded_by | VARCHAR(100) | nullable |

### medical_histories
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| known_allergies | TEXT | |
| chronic_conditions | TEXT | |
| current_medications | TEXT | |
| recent_surgeries | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| patient_id | INT UNSIGNED | FK → patients.id |

### medications
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| route | VARCHAR(100) | e.g. "Oral (By mouth)" |
| drug_name | VARCHAR(255) | |
| dose_strength | VARCHAR(100) | e.g. "500mg" |
| dosage_form | VARCHAR(100) | e.g. Tablet, Suspension |
| timing | VARCHAR(100) | e.g. "Before breakfast" |
| frequency | VARCHAR(100) | e.g. "Three times daily (TDS)" |
| duration | VARCHAR(100) | e.g. "7 days (1 week)" |
| notes | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| prescription_id | INT UNSIGNED | FK → prescriptions.id |

### medications_templates
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### medtel_api_response
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| patient_mobile | VARCHAR(20) | |
| medtel_id | VARCHAR(100) | external Medtel unique ID |
| medtel_patient_id | VARCHAR(100) | e.g. "1-1" |
| thp_id | VARCHAR(100) | third-party health provider ID |
| thp_name | VARCHAR(255) | |
| screening_date | DATE | |
| screening_time | TIME | stored as "HH:MM" |
| response | JSON | large JSON blob |
| created_at | DATETIME | |
| patient_name | VARCHAR(255) | |

### patient_referred
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| service_id | INT UNSIGNED | FK → services.id; nullable |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| referred_by | ENUM('MCO','DOCTOR') | values seen: MCO |
| referrer_id | INT UNSIGNED | FK to mcos.id or doctors.id depending on referred_by |
| referred_service_id | INT UNSIGNED | FK → services.id; nullable |
| referring_date | DATE | |
| referring_time | TIME | nullable |
| referral_reason | TEXT | nullable |
| referred_specialization_id | INT UNSIGNED | FK → specializations.id; nullable |
| urgency_level | INT | e.g. 1-3 |
| frequency | VARCHAR(100) | e.g. "Twice"; nullable |
| no_of_sessions | INT | nullable |
| service_type | ENUM('recurring','one-time') | values seen: recurring, one-time |

### patient_samples
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| sample_type_id | INT UNSIGNED | FK → sample_types.id |
| container_type_id | INT UNSIGNED | FK → container_types.id |
| booking_id | INT UNSIGNED | FK → bookings.id |
| storage_condition | ENUM('ROOM_TEMPERATURE','REFRIGERATED','FROZEN') | values seen: REFRIGERATED, ROOM_TEMPERATURE |
| notes | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| patient_id | INT UNSIGNED | FK → patients.id |
| quantity | VARCHAR(50) | stored as "5ml" or numeric — use VARCHAR |
| status | VARCHAR(50) | values seen: analyzing, lab-submitted, in-transit; may expand |
| barcode | VARCHAR(100) | nullable |

### patient_sample_notes
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| sample_id | INT UNSIGNED | FK → patient_samples.id |
| notes | TEXT | |
| previous_status | VARCHAR(50) | |
| current_status | VARCHAR(50) | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### patient_sample_tests
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### patient_tests
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### prescriptions
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| doctor_id | INT UNSIGNED | FK → doctors.id |
| known_allergies | TEXT | |
| medical_history | TEXT | |
| diagnosis | TEXT | |
| instructions | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### recommendations
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| family_member_id | INT UNSIGNED | FK → family_members.id; nullable |
| service_id | INT UNSIGNED | FK → services.id; nullable |
| recommended_service_id | INT UNSIGNED | FK → services.id; nullable |
| recommended_specialization_id | INT UNSIGNED | FK → specializations.id; nullable |
| recommend_date | DATE | nullable |
| recommend_time | TIME | nullable |
| urgency_level | INT | e.g. 1-3 |
| recommended_by | ENUM('DOCTOR','MCO') | values seen: DOCTOR |
| referrer_id | INT UNSIGNED | FK to doctors.id or mcos.id |
| referral_reason | TEXT | nullable |
| service_type | ENUM('one-time','recurring') | nullable |
| no_of_sessions | INT | nullable |
| frequency | VARCHAR(100) | nullable |
| type | ENUM('SPECIALIST','HOME_CARE_SERVICE') | values seen: SPECIALIST, HOME_CARE_SERVICE |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### recurring_bookings
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| booked_date | DATE | |
| booked_time | INT | minutes from midnight |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### sample_types
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| name | VARCHAR(255) | |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| active | TINYINT(1) | 0/1 |

### templates
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### tests (booking)
> *File exists but is empty (header only)*

| Column | MySQL Type | Notes |
|---|---|---|
| *(empty file — no columns)* | — | Header row absent |

### tests_master
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| test | VARCHAR(100) | test code/name e.g. "bp", "pulse" |
| unit | VARCHAR(50) | e.g. "mmHg", "per min"; nullable |
| male_range | TEXT | range description; nullable |
| female_range | TEXT | range description; nullable |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### booking_items
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| service_id | INT UNSIGNED | FK → services.id |
| quantity | INT | |
| price | DECIMAL(10,2) | price at time of booking |
| created_at | DATETIME | |

---

## Module: sims_med360_payment

### invoices
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| invoice_number | VARCHAR(100) | e.g. SIMS/26-27/00001 |
| payment_id | INT UNSIGNED | FK → payments.id |
| booking_id | INT UNSIGNED | FK → bookings.id |
| patient_id | INT UNSIGNED | FK → patients.id |
| patient_name | VARCHAR(255) | denormalised |
| patient_phone | VARCHAR(20) | denormalised |
| patient_email | VARCHAR(255) | denormalised; nullable |
| patient_uhid | VARCHAR(100) | unique health ID |
| patient_address | TEXT | nullable |
| provider_name | VARCHAR(255) | |
| service_type | VARCHAR(100) | e.g. "Homecare Service" |
| service_name | VARCHAR(255) | |
| service_subtitle | VARCHAR(255) | nullable |
| sac_code | VARCHAR(20) | SAC billing code |
| base_amount | DECIMAL(10,2) | |
| discount | DECIMAL(10,2) | |
| gst_percent | DECIMAL(5,2) | |
| total | DECIMAL(10,2) | |
| transaction_id | VARCHAR(100) | nullable |
| payment_method | VARCHAR(50) | e.g. UPI; nullable |
| upi_id | VARCHAR(100) | nullable |
| date | VARCHAR(50) | stored as "18 Jun 2026"; use VARCHAR or DATE |
| created_at | DATETIME | |

### payments
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| patient_id | INT UNSIGNED | FK → patients.id |
| service_amount | DECIMAL(10,2) | |
| paid_amount | DECIMAL(10,2) | |
| discount | DECIMAL(10,2) | |
| coupon_code | VARCHAR(100) | nullable |
| coupon_discount | DECIMAL(10,2) | |
| payment_gateway | ENUM('RAZORPAY','CASH','UPI') | values seen: RAZORPAY |
| payment_type | VARCHAR(50) | e.g. "Credit Card" |
| gateway_response | JSON | nullable |
| initiator | ENUM('PATIENT','DOCTOR','MCO','ADMIN') | values seen: PATIENT |
| initiator_id | INT UNSIGNED | ID of the initiating entity |
| status | ENUM('PENDING','SUCCESS','FAILED','REFUNDED') | values seen: PENDING |
| created_at | DATETIME | |
| updated_at | DATETIME | |
| gateway_amount | DECIMAL(10,2) | |
| payment_gateway_id | VARCHAR(100) | nullable |
| gst | DECIMAL(5,2) | GST % |
| gst_amount | DECIMAL(10,2) | |

### payment_bookings
| Column | MySQL Type | Notes |
|---|---|---|
| id | INT UNSIGNED | PK AUTO_INCREMENT |
| booking_id | INT UNSIGNED | FK → bookings.id |
| payment_id | INT UNSIGNED | FK → payments.id |
| created_at | DATETIME | |

---

## Module: sims_med360_notifications

### chat_messages *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| conversationId | INT UNSIGNED | conversation/booking reference |
| senderId | VARCHAR(36) | UUID; FK → users.userId |
| senderRole | ENUM('patient','doctor','mco','admin') | values seen: patient |
| message | TEXT | |
| messageType | ENUM('TEXT','IMAGE','FILE') | values seen: TEXT |
| createdAt | DATETIME | |

### exotel *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| from | VARCHAR(20) | caller number |
| to | VARCHAR(20) | callee number |
| createdAt | DATETIME | |
| CallFrom | VARCHAR(20) | nullable |
| CallSid | VARCHAR(100) | Exotel call SID; nullable |
| CallStatus | VARCHAR(50) | e.g. "ringing"; nullable |
| CallTo | VARCHAR(20) | nullable |
| CallType | VARCHAR(50) | e.g. "call-attempt"; nullable |
| Created | VARCHAR(100) | human-readable date string; nullable |
| CurrentTime | DATETIME | nullable |
| DialCallDuration | INT | seconds; nullable |
| DialWhomNumber | VARCHAR(20) | nullable |
| Direction | ENUM('incoming','outgoing') | nullable |
| EndTime | DATETIME | nullable |
| From | VARCHAR(20) | duplicate of from field; nullable |
| StartTime | DATETIME | nullable |
| To | VARCHAR(20) | duplicate of to field; nullable |
| flow_id | VARCHAR(50) | nullable |
| tenant_id | VARCHAR(50) | nullable |

### notifications *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| userId | VARCHAR(36) | UUID; FK → users.userId |
| accessToken | TEXT | Google OAuth access token |
| messagePayload | JSON | FCM message payload |
| fcmToken | VARCHAR(500) | FCM device token |
| deviceId | VARCHAR(255) | |
| fcmResponse | JSON | FCM API response |
| createdAt | DATETIME | |

### sms *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| userId | VARCHAR(36) | UUID; FK → users.userId |
| otp | VARCHAR(20) | OTP value |
| mobile | VARCHAR(20) | |
| type | ENUM('login','service-start','completion') | values seen: login |
| message | JSON | SMS payload JSON |
| smsResponse | JSON | SMS gateway response |
| createdAt | DATETIME | |
| variablesValues | VARCHAR(255) | nullable |
| bookingId | INT UNSIGNED | FK → bookings.id; nullable |
| mcoId | INT UNSIGNED | FK → mcos.id; nullable |

### tokbox_sessions *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| bookingId | INT UNSIGNED | FK → bookings.id |
| name | VARCHAR(255) | participant name |
| sessionId | VARCHAR(255) | OpenTok/Vonage session ID |

### whatsapp *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| userId | VARCHAR(36) | UUID; FK → users.userId |
| mobile | VARCHAR(20) | |
| type | ENUM('welcome','otp','booking_confirm','booking_cancel') | values seen: welcome |
| template | VARCHAR(100) | template name |
| messagePayload | JSON | WhatsApp message payload |
| whatsappResponse | JSON | WhatsApp API response |
| createdAt | DATETIME | |

---

## Module: sims_med360_admin

### coupons *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| code | VARCHAR(100) | coupon code |
| discount | DECIMAL(10,2) | |
| type | ENUM('PERCENTAGE','FLAT') | values seen: PERCENTAGE |
| active | TINYINT(1) | stored as true/false text |
| expiresAt | DATE | expiry date |
| createdAt | DATETIME | |
| updatedAt | DATETIME | |
| applicableTo | JSON | JSON array e.g. ["CRITICAL","ALL"] |
| autoApply | TINYINT(1) | stored as true/false text |
| discountType | ENUM('PERCENTAGE','FLAT') | values seen: PERCENTAGE |
| maxDiscount | DECIMAL(10,2) | nullable |
| minimumOrder | DECIMAL(10,2) | |
| perUserLimit | TINYINT(1) | stored as true/false text |
| usageLimit | INT | |
| nudgeText | TEXT | promotional copy |

### faqs *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| question | TEXT | |
| answer | TEXT | |
| category | VARCHAR(100) | e.g. Booking, Payment |
| active | TINYINT(1) | stored as true/false text |
| sort_order | INT | |
| createdAt | DATETIME | |
| updatedAt | DATETIME | |

### legal_documents *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| type | ENUM('TERMS_AND_CONDITIONS','PRIVACY_POLICY','DISCLAIMER','DATA_SECURITY','CANCELLATION_REFUND') | values seen in data |
| title | VARCHAR(255) | |
| version | VARCHAR(20) | e.g. "1.0" |
| effective_date | DATE | |
| active | TINYINT(1) | stored as true/false text |
| createdAt | DATETIME | |
| updatedAt | DATETIME | |

### settings (admin) *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| name | VARCHAR(255) | setting key e.g. "gst_rate" |
| createdAt | DATETIME | |
| type | ENUM('number','string','boolean') | values seen: number |
| updatedAt | DATETIME | |
| value | VARCHAR(255) | setting value; polymorphic |

### support_contacts *(MongoDB)*
| Column | MySQL Type | Notes |
|---|---|---|
| _id | VARCHAR(24) | PK (ObjectId) |
| label | VARCHAR(255) | |
| phone | VARCHAR(20) | |
| email | VARCHAR(255) | |
| type | ENUM('GENERAL','EMERGENCY','BILLING','TECHNICAL') | values seen in data |
| available_hours | VARCHAR(100) | e.g. "24x7", "Mon-Sat 9am-6pm" |
| priority | INT | |
| active | TINYINT(1) | stored as true/false text |
