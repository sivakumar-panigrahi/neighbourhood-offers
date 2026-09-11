# Neighbourhood Offers

> **Hyperlocal Discount & Rewards Platform**  
> *"Pay for footfall, not for advertising."*

Neighbourhood Offers connects local neighbourhood merchants with nearby shoppers through performance-driven promotions. Unlike traditional digital advertising platforms where shopkeepers pay upfront for impressions, clicks, or ad placements with no guarantee of real-world visits, Neighbourhood Offers enables shopkeepers to **pay strictly for verified footfall**.

Shopkeepers preload a platform points balance (where **1 point = ₹1** of platform discount spend). Points are **deducted only after a customer physically visits the shop and successfully redeems a claim code at the counter POS**.

---

## Table of Contents

- [Overview & Product Purpose](#overview--product-purpose)
- [User Roles & Personas](#user-roles--personas)
- [Key Features](#key-features)
- [Core Business Rules](#core-business-rules)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Demo Accounts & Credentials](#demo-accounts--credentials)
- [Local Development Setup](#local-development-setup)
- [API Documentation](#api-documentation)
- [AI Natural-Language Offer Studio](#ai-natural-language-offer-studio)
- [Redemption, Idempotency & Points Settlement](#redemption-idempotency--points-settlement)
- [Testing & Quality Verification](#testing--quality-verification)
- [Docker Configuration](#docker-configuration)
- [Railway Cloud Deployment Guide](#railway-cloud-deployment-guide)
- [End-to-End Walkthrough Sequence](#end-to-end-walkthrough-sequence)
- [Known Limitations](#known-limitations)
- [License](#license)

---

## Overview & Product Purpose

Traditional retail platforms force local store owners to spend marketing budgets on speculative digital ads. Neighbourhood Offers aligns incentives between merchants, shoppers, and counter cashiers:

* **Why the Platform Exists**: To eliminate wasted advertising spend for small merchants and give shoppers authentic, verified local neighbourhood discounts.
* **Shopper Experience**: Discover live, curated neighbourhood offers filtered by category, city, or shop; claim single-use digital offer vouchers (`NO-XXXXXX`); present vouchers in-store to save money.
* **Shopkeeper Experience**: Create and manage offers, convert natural-language promotional ideas into structured discount rules using the AI Offer Studio, maintain a prepaid points budget, and analyze monthly footfall trends and peak busy days.
* **Counter Staff Experience**: High-speed, distraction-free POS redemption terminal to look up customer claim codes, validate minimum purchase amounts, calculate bill discounts instantly, and complete redemptions idempotently.

---

## User Roles & Personas

The application implements server-side Role-Based Access Control (RBAC) and client-side route guards for three distinct roles:

| Role | Persona | Permissions & Key Capabilities |
| :--- | :--- | :--- |
| **Shopkeeper** | Store Owner / Merchant | Register/manage shop profile, create & control offer lifecycles (`draft`, `active`, `paused`, `expired`), use AI natural-language offer parser, top up points balance, inspect transaction ledger, access monthly footfall analytics. |
| **Shopper** | Customer / Buyer | Browse and search active neighbourhood offers, claim eligible offers (one active claim per offer), view claim codes with instant clipboard copy, track redemption history. |
| **Counter Staff** | Cashier / POS Operator | Fast claim code lookup, gross bill verification, automated discount calculation, idempotent redemption processing. |

---

## Key Features

- **Hyperlocal Discovery**: Real-time browsing of live discount offers with category filters and instant claim vouchers.
- **Offer Lifecycle State Machine**: Strict state transitions (`draft` → `active` ⇄ `paused` → `expired`) preventing invalid operations.
- **AI Natural-Language Offer Studio**: Heuristic and rule-based parser that translates messy merchant text (e.g. *"20% off all dairy items above ₹300 till Friday"*) into structured discount parameters with confidence scoring and safety warnings.
- **Human-in-the-Loop AI Workflow**: AI parsing strictly outputs a reviewable proposal; offers are never automatically saved or activated without explicit merchant confirmation.
- **Collision-Resistant Claim Codes**: High-entropy alphanumeric codes (`NO-XXXXXX`) generated deterministically per claim.
- **Idempotent Redemption Engine**: Header-driven (`Idempotency-Key`) redemption API preventing duplicate billing or double point deductions during network retries.
- **Atomic Double-Entry Points Ledger**: PostgreSQL row-level locking (`SELECT ... FOR UPDATE`) guarantees race-condition-free point deductions during concurrent checkouts.
- **Monthly Footfall Analytics**: Computes total gross sales, total discounts granted, net customer billings, remaining points, and identifies peak footfall ("busy days").
- **Responsive Web UI**: Built with React 18, TypeScript, and accessible modern CSS with dark-mode accents and responsive data cards.

---

## Core Business Rules

The platform enforces the following domain rules at both the API and database levels:

1. **Ownership Authorization**: A shopkeeper can only view, edit, activate, or manage offers and points belonging to their own shop. Cross-shop mutations are rejected with `403 Forbidden` or `404 Not Found`.
2. **Offer Expiry**: Expired offers (`valid_until < now()`) cannot be claimed by shoppers or redeemed at the counter.
3. **Claim Eligibility**: Only authenticated shoppers can claim offers. A shopper cannot hold multiple active unredeemed claims for the same offer simultaneously.
4. **Counter-Only Redemption**: Only counter staff assigned to the corresponding shop can redeem claims. Shoppers and shopkeepers cannot redeem claims.
5. **Idempotency Protection**: Replaying a redemption request with the same `Idempotency-Key` and payload returns the cached result without creating a duplicate redemption record or deducting additional points. Submitting a different payload with a reused key raises `409 Conflict`.
6. **Points Deduction on Redemption**: Points are deducted **only upon successful in-store redemption**, never on offer creation or claim generation.
7. **Sufficient Balance Requirement**: If a shopkeeper's points balance is less than the calculated discount amount, redemption is rejected (`INSUFFICIENT_POINTS_BALANCE`).
8. **Discount Capping**: Calculated percentage discounts cannot exceed the gross bill amount.
9. **Minimum Spend Validation**: A claim cannot be redeemed if the gross purchase amount is below the offer's `min_purchase_amount`.

---

## Architecture & Tech Stack

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          React 18 + TypeScript                          │
│        (Role-Based UI: Shopper Feed, Shopkeeper Studio, Counter POS)    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTPS / JSON REST API
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          FastAPI (Python 3.11)                          │
│   ┌────────────────┬──────────────────┬─────────────────────────────┐   │
│   │  Auth & RBAC   │  Offer Lifecycle │  AI Natural-Language Parser │   │
│   ├────────────────┼──────────────────┼─────────────────────────────┤   │
│   │  Claims Engine │  POS Redemption  │  Points Ledger & Reports    │   │
│   └────────────────┴──────────────────┴─────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ SQLAlchemy 2.0 ORM (psycopg3)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PostgreSQL 15 (Alembic Migrated)                   │
│   • users              • shops              • offers                    │
│   • claims             • redemptions        • points                    │
│   • points_ledger      • idempotency_keys                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Breakdown

- **Frontend**: React 18, TypeScript, Vite, Vanilla CSS Design System, Lucide Icons.
- **Backend**: FastAPI (Python 3.11), Pydantic v2, Uvicorn (ASGI).
- **Database & ORM**: PostgreSQL 15, SQLAlchemy 2.0, Alembic database migrations.
- **Security**: JWT Bearer Tokens (HS256), Argon2 / Bcrypt password hashing.
- **Deployment & Containers**: Docker (Multi-stage builds), NGINX (Alpine SPA server), Railway Cloud.

---

## Project Structure

```text
neighbourhood-offers/
├── backend/
│   ├── alembic/                # Alembic database migrations (initial tables, indices, triggers)
│   ├── app/
│   │   ├── api/                # API route definitions and security dependencies
│   │   │   ├── dependencies.py # JWT validation and RBAC guards
│   │   │   └── routes/         # auth, shops, offers, claims, redemptions, reports
│   │   ├── core/               # App configuration, security helpers (passwords, tokens)
│   │   ├── db/                 # Database session engine
│   │   ├── models/             # SQLAlchemy ORM database models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Domain business logic (claims, redemption, parser, points)
│   │   └── main.py             # FastAPI entry point and CORS configuration
│   ├── scripts/
│   │   └── seed.py             # Deterministic, idempotent database seeding
│   ├── tests/                  # Pytest regression suite (75 test cases)
│   ├── Dockerfile              # Production Python container
│   ├── pytest.ini              # Test configuration
│   ├── requirements.txt        # Backend dependencies
│   └── start.sh                # Production entrypoint (runs migrations, seed, uvicorn)
├── frontend/
│   ├── src/
│   │   ├── api/                # Typed REST API clients
│   │   ├── components/         # Modals, Claim badges, Loading spinners, Empty states
│   │   ├── context/            # AuthContext (state management, session persistence)
│   │   ├── layouts/            # AppLayout with dynamic navigation and AuthLayout
│   │   ├── pages/              # Role-specific portal views
│   │   │   ├── counter/        # Cashier POS redemption terminal
│   │   │   ├── shopkeeper/     # Dashboard, Offers, AI Create, Points, Reports
│   │   │   └── shopper/        # Discover offers, My Claims wallet, Profile
│   │   ├── routes/             # Role-based protected route handlers
│   │   └── types/              # Domain TypeScript interfaces
│   ├── Dockerfile              # Multi-stage build (Node 20 builder + NGINX runner)
│   ├── nginx.conf              # SPA routing fallback and security headers
│   ├── package.json            # Frontend dependencies and scripts
│   └── vite.config.ts          # Vite build configuration
├── docker-compose.yml          # Local container orchestration (Postgres, Backend, Frontend)
├── Makefile                    # Developer workflow shortcuts
└── README.md                   # Production documentation
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Type | Default / Example | Purpose |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | String | `"Neighbourhood Offers"` | Application display name |
| `ENVIRONMENT` | String | `development` / `production` | Environment mode |
| `DATABASE_URL` | String | `postgresql+psycopg://user:pass@localhost:5432/neighbourhood` | PostgreSQL connection URI |
| `CORS_ORIGINS` | String | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed frontend origins |
| `JWT_SECRET_KEY` | String | `safe_placeholder_secret_key_change_in_prod` | Secret key used for signing JWT access tokens |
| `JWT_ALGORITHM` | String | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `120` | Access token lifespan in minutes |
| `SEED_DEMO_DATA` | Boolean | `true` | Automatically run seed script on startup |
| `AI_PROVIDER` | String | `fallback` | AI parsing engine (`fallback`, `gemini`, `openai`) |
| `AI_API_KEY` | String | `""` | Optional API key for external LLM provider |
| `AI_MODEL` | String | `""` | Optional model identifier for external LLM |

### Frontend (`frontend/.env`)

| Variable | Type | Default / Example | Purpose |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | String | `http://localhost:8000` | Backend API base URL for client requests |

*Note: Never commit real production secrets to version control. Safe `.env.example` templates are provided in both `backend/` and `frontend/`.*

---

## Demo Accounts & Credentials

The database includes 6 pre-seeded demonstration accounts covering all three user roles.

**Universal Demo Password:** `DemoPassword123!`

| Role | Name | Email | Description & Pre-configured Data |
| :--- | :--- | :--- | :--- |
| **Shopkeeper** | Anitha | `anitha.demo@example.com` | Owner of *Anitha's Grocery* (5,051 points, active offers, full monthly reports) |
| **Shopkeeper** | Rahul | `rahul.demo@example.com` | Owner of *Rahul's Fashion Corner* (2,200 points, active clothing offers) |
| **Shopper** | Priya | `priya.demo@example.com` | Active neighbourhood shopper with active vouchers and past redemptions |
| **Shopper** | Arjun | `arjun.demo@example.com` | Active neighbourhood shopper with fresh wallet |
| **Counter Staff** | Ravi | `ravi.demo@example.com` | Assigned Cashier for *Anitha's Grocery* |
| **Counter Staff** | Meena | `meena.demo@example.com` | Assigned Cashier for *Rahul's Fashion Corner* |

---

## Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ or 20+ LTS & npm
- PostgreSQL 15+

### 2. Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a Python virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template and configure DATABASE_URL
cp .env.example .env

# 5. Apply database migrations
alembic upgrade head

# 6. Seed demo accounts and initial shop data
python -m scripts.seed

# 7. Start the FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend API available at: `http://127.0.0.1:8000`*

### 3. Frontend Setup
```bash
# 1. Open a new terminal and navigate to frontend
cd frontend

# 2. Install npm packages
npm install

# 3. Copy environment template
cp .env.example .env

# 4. Start the Vite dev server
npm run dev
```
*Frontend web application available at: `http://localhost:5173`*

---

## API Documentation

FastAPI generates interactive OpenAPI documentation automatically:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
- **Health Check**: `http://localhost:8000/health` (Returns `{"status": "ok", "app": "Neighbourhood Offers"}`)

### Primary API Endpoints

| Method | Endpoint | Access / Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Public | Register a new user (Shopper or Shopkeeper) |
| `POST` | `/auth/login` | Public | Authenticate and obtain JWT Bearer token |
| `GET` | `/auth/me` | Authenticated | Get profile details and role of current user |
| `GET` | `/shops` | Authenticated | List all active neighbourhood shops |
| `GET` | `/shops/me` | Shopkeeper | Retrieve shop profile for authenticated merchant |
| `POST` | `/shops` | Shopkeeper | Create initial shop profile |
| `GET` | `/shops/me/points` | Shopkeeper | View current points balance and transaction ledger |
| `POST` | `/shops/me/points/top-up` | Shopkeeper | Top up shop points balance |
| `GET` | `/shops/me/redemptions`| Shopkeeper | View full redemption history for merchant's shop |
| `GET` | `/offers` | Authenticated | Browse active discount offers with filters |
| `GET` | `/offers/my` | Shopkeeper | List all offers created by merchant's shop |
| `POST` | `/offers` | Shopkeeper | Create a new offer in `draft` status |
| `POST` | `/offers/parse` | Shopkeeper | AI natural-language offer parser |
| `POST` | `/offers/{id}/activate`| Shopkeeper | Activate a draft or paused offer |
| `POST` | `/offers/{id}/pause` | Shopkeeper | Pause an active offer |
| `POST` | `/offers/{id}/resume` | Shopkeeper | Resume a paused offer |
| `POST` | `/offers/{id}/claim` | Shopper | Claim an active offer and receive claim code |
| `GET` | `/claims/my` | Shopper | Retrieve all claimed vouchers for current shopper |
| `GET` | `/claims/{id}` | Shopper | View individual claim status and code |
| `POST` | `/redemptions` | Counter Staff | Process in-store claim redemption with idempotency |
| `GET` | `/redemptions/code/{code}` | Counter Staff | Inspect claim details prior to redemption |
| `GET` | `/reports/monthly` | Shopkeeper | Retrieve aggregated monthly footfall & financial analytics |

---

## AI Natural-Language Offer Studio

The AI Offer Studio (`/app/shopkeeper/ai-create`) enables shopkeepers to generate structured offers from informal natural-language descriptions.

### The 5-Stage Human-in-the-Loop Workflow

```text
[ Natural-Language Promo Input ]
            │
            ▼
[ POST /offers/parse ]  ───► Deterministic Heuristic Parser / LLM
            │
            ▼
[ Structured Offer Proposal ] (Discount %, Min Bill, Expiry, Confidence, Warnings)
            │
            ▼
[ Merchant Review & Edit Form ] (Merchant verifies/modifies all fields)
            │
            ▼
[ Create Draft Offer (POST /offers) ]
            │
            ▼
[ Explicit Activation (POST /offers/{id}/activate) ]
```

### Safety & Integrity Guarantees
- **Parsing Does NOT Create Offers**: Calling `/offers/parse` is a pure read/transform operation that never writes records to the database.
- **Deterministic Heuristics Engine**: The platform includes a fallback parsing engine capable of extracting discount types (percentage vs. fixed), minimum purchase thresholds, category tags, and relative dates (e.g. *"until Sunday"*, *"next weekend"*) without external API dependencies.
- **Safety Warnings**: The parser emits explicit warnings when inputs have low confidence, ambiguous cultural references (e.g. *"Diwali special"* without exact date), or missing expiry dates.

---

## Redemption, Idempotency & Points Settlement

```text
Customer presents Claim Code (NO-XXXXXX)
                   │
                   ▼
Counter Staff enters Code + Gross Bill into POS Terminal
                   │
                   ▼
POST /redemptions  (with Idempotency-Key header)
                   │
                   ├──► 1. Check Idempotency Key cache
                   ├──► 2. Validate Counter Staff shop authorization
                   ├──► 3. Validate Claim status == ACTIVE and not expired
                   ├──► 4. Validate Gross Bill >= min_purchase_amount
                   ├──► 5. Calculate Discount & Cap at Gross Bill
                   ├──► 6. Lock Shop Points row (SELECT ... FOR UPDATE)
                   ├──► 7. Validate Points Balance >= Discount Amount
                   │
                   ▼
Atomic Database Transaction:
  • Decrement shop points_balance by discount amount
  • Insert immutable PointsTransaction record
  • Update Claim status to 'redeemed'
  • Insert Redemption record with bill & discount details
                   │
                   ▼
Return Printable POS Receipt (Gross Bill, Discount, Net Payable, Points Deducted)
```

---

## Testing & Quality Verification

### 1. Backend Pytest Suite
The backend is protected by a comprehensive test suite with **75 passing tests** across 7 domain modules:

```bash
cd backend
pytest -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: backend, configfile: pytest.ini, testpaths: tests
collected 75 items

tests/test_auth.py .............                                         [ 17%]
tests/test_claims.py .........                                           [ 29%]
tests/test_offer_parser.py ...............                               [ 49%]
tests/test_offers.py ...............                                     [ 69%]
tests/test_redemptions.py ...........                                    [ 84%]
tests/test_reporting.py .......                                          [ 93%]
tests/test_seed.py .....                                                 [100%]

======================= 75 passed, 2 warnings in 17.45s =======================
```

### 2. Frontend Production Build
Validate TypeScript types and bundling with zero compilation errors:

```bash
cd frontend
npm run build
```

---

## Docker Configuration

The repository includes multi-stage Dockerfiles and a root `docker-compose.yml` for unified local container execution.

### Services Defined:
1. **`postgres`**: PostgreSQL 15 Alpine database with automated healthchecks.
2. **`backend`**: FastAPI Python 3.11 container with non-root security execution, automatic startup migration (`alembic upgrade head`), and optional initial seeding.
3. **`frontend`**: Multi-stage build (Node 20 Alpine builder compiling Vite assets → NGINX Alpine serving static SPA with client-side route fallback).

### Running with Docker Compose:
```bash
# 1. Validate Docker Compose configuration
docker compose config

# 2. Build and start all services
docker compose up -d --build

# 3. View container logs
docker compose logs -f

# 4. Stop all services
docker compose down
```

*Note: Local Docker configuration has been validated. Production cloud hosting is managed on Railway.*

---

## Railway Cloud Deployment Guide

The application is structured for continuous deployment to **Railway**:

```text
                    INTERNET
                       │
                       ▼
              ┌─────────────────┐
              │ React + Vite    │  (Railway Frontend Service - NGINX)
              │   Frontend      │  Port: $PORT (Assigned by Railway)
              └────────┬────────┘
                       │ HTTPS API Calls (VITE_API_BASE_URL)
                       ▼
              ┌─────────────────┐
              │ FastAPI Backend │  (Railway Backend Service - Dockerfile)
              │                 │  Port: $PORT | Health: /health
              └────────┬────────┘
                       │ TCP / SSL (DATABASE_URL)
                       ▼
              ┌─────────────────┐
              │   PostgreSQL    │  (Railway Managed PostgreSQL Database)
              └─────────────────┘
```

### Deployment Configuration Steps:

1. **Create Railway Project**: Connect your GitHub repository (`https://github.com/sivakumar-panigrahi/neighbourhood-offers.git`).
2. **Provision PostgreSQL Database**: Add a PostgreSQL database service; Railway exposes `DATABASE_URL`.
3. **Configure Backend Service**:
   - Root Directory: `/backend`
   - Build: `backend/Dockerfile`
   - Healthcheck: `/health`
   - Variables:
     ```env
     DATABASE_URL=${{Postgres.DATABASE_URL}}
     ENVIRONMENT=production
     APP_NAME="Neighbourhood Offers"
     JWT_SECRET_KEY=generate-a-strong-random-secret-key-here
     JWT_ALGORITHM=HS256
     JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
     CORS_ORIGINS=https://${{Frontend.RAILWAY_PUBLIC_DOMAIN}}
     SEED_DEMO_DATA=true
     AI_PROVIDER=fallback
     ```
4. **Configure Frontend Service**:
   - Root Directory: `/frontend`
   - Build: `frontend/Dockerfile`
   - Variables:
     ```env
     VITE_API_BASE_URL=https://${{Backend.RAILWAY_PUBLIC_DOMAIN}}
     ```
5. **Continuous Delivery**: Future commits pushed to `master` will trigger automated Railway builds and rolling deployments.

---

## End-to-End Walkthrough Sequence

Follow this **3–5 minute evaluation walkthrough** to inspect all user flows:

1. **Landing Page**: Open the homepage to review product overview, live offer previews, and instant demo quick-logins.
2. **Shopper Login**: Log in as Priya (`priya.demo@example.com` / `DemoPassword123!`).
3. **Discover an Offer**: Browse the marketplace feed and filter by "Grocery" or search for active deals.
4. **Claim the Offer**: Click "View Details & Claim" on an active discount.
5. **Show Claim Code**: Observe the generated voucher code (e.g. `NO-7K8M9P`) and copy it to clipboard.
6. **Counter Login**: Sign out and log in as Ravi (`ravi.demo@example.com` / `DemoPassword123!`).
7. **Redeem Claim**: Open POS Terminal, paste the claim code, enter a gross purchase bill (e.g. `₹1,000`), and click "Process Redemption".
8. **Show Discount & Points**: Review the generated POS receipt showing the applied discount, customer net bill, and exact point deduction from the shop.
9. **Retry Redemption**: Attempt to redeem the same code again with the same bill amount.
10. **Show Duplicate Protection**: Verify the idempotency engine safely handles the repeat request without double-deduction.
11. **Shopkeeper Login**: Sign out and log in as Anitha (`anitha.demo@example.com` / `DemoPassword123!`).
12. **Dashboard Overview**: Inspect the metric cards displaying Points Balance, Monthly Footfall, and Peak Traffic Day.
13. **Offers Management**: Navigate to `/app/shopkeeper/offers` to view active and draft promotions, and toggle status.
14. **AI Offer Studio**: Navigate to `/app/shopkeeper/ai-create`.
15. **Parse Natural-Language Offer**: Input: *"Give 25% off all bakery items on bills above ₹400 until Sunday"* and click "Parse Offer with AI".
16. **Review Parsed Rules**: Review the extracted discount rules, minimum purchase, confidence score, and warnings.
17. **Create Draft**: Click "Confirm & Create Draft Offer" to save the structured promotion.
18. **Reporting & Insights**: Open `/app/shopkeeper/reports` to inspect monthly discount spend and the busy day footfall breakdown.
19. **Explain Business Value**: Review the merchant's ledger where costs are tied strictly to customer redemptions.

> *"Pay for footfall, not for advertising."*

---

## Known Limitations

- **Direct SMS / WhatsApp Gateway**: Vouchers are displayed digitally in-app with clipboard copy support; SMS/WhatsApp dispatch requires an external Twilio or Gupshup integration.
- **Payment Gateway Integration**: Points balance top-up currently uses a simulation endpoint rather than a live external Razorpay/Stripe checkout.
- **Single Shop per Merchant**: In the current MVP schema, each shopkeeper user account manages one primary physical retail store.

---

## License

This project is licensed under the MIT License. Designed and engineered for the Neighbourhood Offers Technical Assessment.
