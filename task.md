# Task Plan: Building Rento as a Fully Working Project (for Antigravity)

**How to use this file:** This breaks the *actual implementation* of Rento (not just the report) into 15 sequential parts. Each part contains the exact prompt to give Antigravity to build that part of the system. Build strictly in order — later parts depend on earlier ones (database → auth → core APIs → AI modules → frontend → deployment). **After finishing each part, stop and ask the user for confirmation before proceeding to the next part.**

---

## Part 1 — Project Scaffolding & Environment Setup
**Goal:** Stand up the repo structure, tooling, and dev environment.

**Prompt to give Antigravity:**
> "Scaffold a full-stack project called `rento` with this structure: a `backend/` folder using FastAPI (Python), a `frontend/` folder using React, a `database/` folder for migrations, and an `ai-services/` folder for standalone AI microservices. Set up virtual environment, requirements.txt, package.json, a `.env.example` file for secrets (DB URL, JWT secret, maps/weather API keys, payment gateway keys), a README with setup instructions, and a basic `docker-compose.yml` that runs Postgres, backend, and frontend together. Verify the backend starts and returns a health-check endpoint."

**Deliverable:** Runnable skeleton project (backend health-check + frontend boots) with Docker Compose.

⏸️ **STOP — confirm with user before proceeding to Part 2.**

---

## Part 2 — Database Schema & Migrations
**Goal:** Create the relational schema backing every module in the SRS.

**Prompt to give Antigravity:**
> "Using PostgreSQL and SQLAlchemy (with Alembic for migrations), create the schema for: User (base, with role: renter/host/admin), Vehicle (with isEV, healthScore, pricePerDay), EVDetails, Booking, Payment, Inspection (pickup/return, photoUrls, flags), Trip (telematicsLog, safetyScore), TrustScore, Hub, Review, and Notification. Add foreign keys matching the class diagram (Booking links Renter, Vehicle, Payment, Inspection, Trip, Review). Generate and run the initial migration, and seed the database with 5 sample users, 5 vehicles, and 2 hubs for testing."

**Deliverable:** Working migrations + seeded local database.

⏸️ **STOP — confirm with user before proceeding to Part 3.**

---

## Part 3 — Authentication & User Management
**Goal:** Implement FR-1 (registration/login) with role-based access.

**Prompt to give Antigravity:**
> "Implement authentication endpoints: register, login, refresh token, and logout, using hashed passwords (bcrypt/argon2) and JWT-based auth. Support three roles — renter, host, admin — with role-based route protection middleware. Add an identity-verification stub endpoint (e.g., license/ID upload placeholder). Write tests confirming a renter cannot access admin-only routes and vice versa."

**Deliverable:** Working auth system with role-based access control and passing tests.

⏸️ **STOP — confirm with user before proceeding to Part 4.**

---

## Part 4 — Vehicle Listing Module
**Goal:** Let hosts list, edit, and manage vehicle availability.

**Prompt to give Antigravity:**
> "Build CRUD endpoints for vehicles: create listing (host-only), update availability/pricing, upload vehicle photos, soft-delete a listing, and a public search/list endpoint with filters (location, price range, EV/non-EV, availability dates). Include the EVDetails sub-resource (battery capacity, charging type) when isEV is true. Write integration tests for listing creation and search filtering."

**Deliverable:** Working vehicle listing + search API.

⏸️ **STOP — confirm with user before proceeding to Part 5.**

---

## Part 5 — Booking Core Module
**Goal:** Implement the booking lifecycle skeleton (create/cancel/status) matching the state-chart.

**Prompt to give Antigravity:**
> "Implement the Booking entity's lifecycle exactly matching this state machine: Created → Pending Approval → Confirmed → Pickup Inspection → Ongoing Trip → Return Inspection → Completed, with side branches to Rejected, Disputed→Resolved, and Cancelled. Build endpoints to create a booking request, transition its status, and cancel it (only allowed pre-pickup). Enforce valid transitions only — reject any invalid state change with a clear error. Write tests covering at least one full happy-path booking and one cancellation."

**Deliverable:** Booking state machine implemented and enforced at the API level.

⏸️ **STOP — confirm with user before proceeding to Part 6.**

---

## Part 6 — AI Dynamic Pricing Engine
**Goal:** Recommend a rental price based on demand/context signals.

**Prompt to give Antigravity:**
> "Build a standalone `pricing-service` microservice. Start with a rule-based model that adjusts a vehicle's base price using: day-of-week multiplier, upcoming holiday flag (via a public holiday API or static calendar), a mocked weather signal, and a simple demand multiplier based on how many active bookings exist in that vehicle's city. Expose a `/recommend-price` endpoint the backend calls when a listing is viewed or price-refreshed. Document how this can later be swapped for an ML model without changing the API contract."

**Deliverable:** Working pricing microservice returning a recommended price within 2-3 seconds.

⏸️ **STOP — confirm with user before proceeding to Part 7.**

---

## Part 7 — AI Natural-Language Car Matching
**Goal:** Let renters describe their trip in plain language and get ranked matches.

**Prompt to give Antigravity:**
> "Build a `matching-service` that accepts a free-text query (e.g., 'cheap EV for a weekend trip with a child seat') and returns ranked vehicle matches. Start with a keyword/embedding-based approach (e.g., sentence-transformers or a simple keyword-weighted scorer) against vehicle metadata (price, EV status, extras available, location). Expose a `/match` endpoint the frontend search bar calls. Write a few test queries and confirm reasonable ranking."

**Deliverable:** Working NLP matching endpoint with test queries.

⏸️ **STOP — confirm with user before proceeding to Part 8.**

---

## Part 8 — Car Health Score Module
**Goal:** Compute and expose a Car Health Score (CHS) per vehicle.

**Prompt to give Antigravity:**
> "Build a `scoring-service` module that computes a Car Health Score (0-100) from structured inputs: last-service date, reported mileage, host-declared condition flags, and (later) inspection-derived damage flags. Start rule-based (weighted deductions). Expose `/vehicle/{id}/health-score` and store the score on the Vehicle record. Ensure the Decision Table logic from Part 10 can read this score."

**Deliverable:** Working Car Health Score computation and storage.

⏸️ **STOP — confirm with user before proceeding to Part 9.**

---

## Part 9 — AI Pickup/Return Damage Inspection
**Goal:** Compare pickup vs. return photos and flag new damage.

**Prompt to give Antigravity:**
> "Build an `inspection-service` using OpenCV/scikit-learn (or a pretrained CV model) that: (1) accepts 8-10 pickup photos and stores them as the baseline, (2) accepts return photos, (3) runs image differencing/structural similarity comparison between corresponding angles, (4) flags regions with significant visual difference as possible new damage, and (5) generates a structured evidence report (JSON + a simple rendered summary) for dispute resolution. Expose `/inspection/pickup` and `/inspection/return` endpoints. Test with sample before/after images including one with an obvious added scratch."

**Deliverable:** Working image-comparison inspection pipeline producing an evidence report.

⏸️ **STOP — confirm with user before proceeding to Part 10.**

---

## Part 10 — Trust Score & Booking Approval Engine
**Goal:** Implement the exact approval logic from the Decision Table/Tree.

**Prompt to give Antigravity:**
> "Implement a Trust Score module for renters (based on completed trips, cancellations, past damage flags) and a Booking Approval Engine that follows this exact logic: Trust Score ≥80 + payment verified + Car Health Score ≥70 → auto-approve; Trust Score ≥80 + payment not verified → manual review; Trust Score 50-79 + low Car Health Score → manual review; Trust Score 50-79 + payment not verified → reject; Trust Score <50 → always reject. Wire this into the booking creation flow from Part 5. Write unit tests covering all 6 rules (R1-R6) from the decision table."

**Deliverable:** Approval engine passing tests for all 6 decision-table rules.

⏸️ **STOP — confirm with user before proceeding to Part 11.**

---

## Part 11 — EV Range & Charging Guidance
**Goal:** Give EV renters usable range vs. trip distance and charging stop suggestions.

**Prompt to give Antigravity:**
> "Extend the EVDetails module to compute usable range from battery capacity/percentage and a simple efficiency factor. Build an endpoint that takes a planned trip distance and current charge level, returns whether the trip is feasible on current charge, and if not, suggests charging stops using a maps/EV-charger API (or a mocked list of charging stations for the prototype). Test with a trip distance greater than usable range to confirm a charging stop is recommended."

**Deliverable:** Working EV range-check and charging-recommendation endpoint.

⏸️ **STOP — confirm with user before proceeding to Part 12.**

---

## Part 12 — Driver Safety Score, Telematics & Collision Detection
**Goal:** Track trip telematics and compute a safety score; detect collisions.

**Prompt to give Antigravity:**
> "Build a `telematics-service` that accepts simulated accelerometer/GPS data streamed during a trip (since real hardware isn't available in prototype), computes a Driver Safety Score from hard-braking/acceleration/speed-variance events, and stores it against the Trip record. Add collision-detection logic that flags a probable collision when deceleration exceeds a threshold, and triggers an emergency workflow stub (log event, mock 'notify emergency contact' + 'share location'). Write a test that feeds a simulated hard-braking spike and confirms the safety score drops and an emergency event fires above threshold."

**Deliverable:** Working telematics scoring + collision-detection stub.

⏸️ **STOP — confirm with user before proceeding to Part 13.**

---

## Part 13 — Group Bookings, Cost-Splitting & Bundled Extras
**Goal:** Support multi-participant bookings and add-ons.

**Prompt to give Antigravity:**
> "Extend the Booking module to support multiple participants per booking, with automatic itemized cost-splitting (equal split by default, with an option for custom split). Add a bundled-extras system (child seat, Wi-Fi, camping kit, etc.) that can be attached to a booking with per-item pricing added to the total. Update `calculateCost()` accordingly. Write a test booking with 3 participants and 2 extras, confirming totals split correctly."

**Deliverable:** Group booking + extras working with correct cost-splitting.

⏸️ **STOP — confirm with user before proceeding to Part 14.**

---

## Part 14 — Payments, Gamification/Rewards, Carbon Score & Notifications
**Goal:** Wire in payment processing, host rewards, eco-scoring, and notifications.

**Prompt to give Antigravity:**
> "Integrate a sandbox/test-mode payment gateway (e.g., Stripe test mode) for processing rental payments and refunds — never store raw card data. Build a gamification module that awards hosts points based on cleanliness ratings, response time, and cancellation rate, assigning tiers (Bronze/Silver/Gold). Build a simple Carbon/Eco Score calculator per trip based on vehicle type and distance (with EVs scoring higher). Add a notification service (email or in-app) that fires on booking confirmation, approval/rejection, and reward-tier changes. Test the full payment-to-notification chain on a sample booking."

**Deliverable:** Working payments, rewards, eco-score, and notification pipeline.

⏸️ **STOP — confirm with user before proceeding to Part 15.**

---

## Part 15 — Frontend Integration, End-to-End Testing & Deployment
**Goal:** Connect all backend modules into a usable UI and ship a working demo.

**Prompt to give Antigravity:**
> "Build the React frontend screens: registration/login, search + AI match results, vehicle listing detail with Car Health Score, booking flow with price recommendation, pickup/return photo capture UI, host dashboard (listings, approvals, rewards tier), admin dashboard (disputes, moderation), and a trip screen showing EV range/safety score live. Wire every screen to the real backend endpoints built in Parts 2-14. Write end-to-end tests covering: register → search → book → pickup inspection → trip → return inspection → payment → review. Finally, prepare a deployment config (Docker Compose for local demo, or a simple cloud deploy script) and a demo script/checklist for presenting the working prototype."

**Deliverable:** Fully connected, end-to-end working Rento prototype, tested and deployable.

⏸️ **STOP — confirm with user that the full working project is complete before wrapping up.**

---

### Notes on Using This Plan
- Feed these prompts to Antigravity **one part at a time, in order** — do not skip ahead, since each part depends on the database/auth/booking foundation built earlier.
- After each part, actually run the tests/demo before confirming and moving on — don't just accept the code as "done."
- If Antigravity produces something that doesn't match a prompt's intent, revise and re-run that same part before advancing — don't patch it later from a future part.
- This plan builds the AI modules rule-based first per the Feasibility Study; upgrading any module (pricing, matching, CV inspection, telematics) to a real ML model can be layered in later without changing the API contracts established here.
