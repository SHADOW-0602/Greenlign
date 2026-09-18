# Greenlign

> **Audit-grade, AI-assisted greenhouse gas accounting and decarbonization intelligence platform.**

Greenlign pairs LLM-assisted workflow automation (Groq `llama-3.3-70b-versatile`) with pure, deterministic Python arithmetic, referential integrity guards, cryptographic audit provenance, statutory ESG disclosure generation, greenwashing detection, decarbonization scenario modeling, and autonomous Scope 3 supplier engagement.

---

## 🏛️ Core Architectural Principle

> **Non-Negotiable Rule:** All arithmetic that produces a final $t\text{CO}_2e$ figure **MUST** be executed by a deterministic Python function (`Decimal` arithmetic) backed by unit tests. **Zero LLM completion or estimation is permitted in the calculation path.**
>
> LLMs are restricted strictly to:
> 1. Classifying raw activity descriptions into GHG Protocol Scopes and categories (with confidence scoring).
> 2. Assisting human auditors by cross-examining public narrative CSR claims against verified ledger data.
> 3. Generating personalized Scope 3 supplier outreach inquiries (with deterministic fallbacks).

---

## ✨ Platform Capabilities (Phases 0 – 7)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   GREENLIGN PLATFORM                                   │
├────────────────────────────────┬────────────────────────────────┬──────────────────────┤
│ 1. INGESTION & REDACTION       │ 2. SCOPE CLASSIFICATION        │ 3. CALCULATION       │
│ • PDF utility bills (OCR)      │ • Groq LLM Scope 1/2/3         │ • EPA eGRID / DEFRA  │
│ • CSV/XLSX ERP activity logs   │ • GHG Protocol taxonomy        │ • Deterministic math │
│ • Presidio PII tokenization    │ • Human review queue           │ • Traceable formula  │
├────────────────────────────────┼────────────────────────────────┼──────────────────────┤
│ 4. AUDIT PROVENANCE            │ 5. REGULATORY DISCLOSURES      │ 6. GREENWASHING SCAN │
│ • Sub-200ms evidence trees     │ • California SB 253            │ • Statistical Z-score│
│ • Calculation → Factor → File  │ • EU CSRD ESRS E1              │ • YoY variance check │
│ • Referential integrity guards │ • Footnoted PDF generator      │ • Narrative check    │
├────────────────────────────────┴────────────────────────────────┴──────────────────────┤
│ 7. EXECUTIVE DASHBOARD, SIMULATOR & SUPPLIER OUTREACH                                  │
│ • Executive ESG Carbon Intelligence Dashboard (KPIs, scope breakdown, hotspots, trends)│
│ • Decarbonization Scenario Simulator (Solar PPA, EV, Heat Pumps, MACC $/tCO2e curve)   │
│ • Autonomous Scope 3 Supplier Outreach Agent (Missing data detection, Groq outreach)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Ingestion Pipeline & PII Guardrails (Phase 1)
- **Multi-Format Ingestion**: Supports CSV, XLSX, and multi-page scanned PDF utility bills via `unstructured` and `pytesseract`.
- **Flexible Column Mapping**: Dynamically maps heterogeneous ERP line items to canonical activity records.
- **Presidio PII Redaction**: Tokenizes sensitive corporate identifiers, vendor account numbers, and supplier details before any LLM ingestion.
- **Asynchronous Task Queue**: Large document parsing executed off-thread via Celery workers backed by Redis.

### 2. LLM-Assisted Scope Classification (Phase 2)
- **Structured GHG Protocol Classification**: Maps raw activity descriptions to Scope 1, Scope 2, or Scope 3 categories (e.g., *Scope 3.6 Business Travel*, *Scope 1 Mobile Combustion*).
- **Confidence Scoring & Routing**: Computes classification confidence ($0.0 - 1.0$). Classifications below the threshold ($< 0.75$) are automatically routed to the human-in-the-loop review queue.
- **Auditor Override & Governance**: Human adjustments update the database, retrain/adjust routing metadata, and log an `AuditLogEntry`.

### 3. Factor Matching & Deterministic Calculation Engine (Phase 3)
- **Versioned Factor Registry**: Sourced, dated emission factor tables (EPA GHG Hub, EPA eGRID 2025, DEFRA 2025).
- **Exact Factor Matching**: Deterministic multi-attribute matching on `(activity_type, geography, effective_dates)`.
- **Pure Arithmetic**: Python `Decimal` arithmetic handles unit conversion and multiplication with zero floating-point imprecision.
- **Formula Provenance**: Stores transparent, human-readable math formulas directly on each calculation record.

### 4. Audit Provenance Trail & Governance Log (Phase 4)
- **Sub-200ms Evidence Tree**: Traces any reported carbon figure back through its mathematical formula, emission factor version, activity line item, and raw source document.
- **Referential Integrity**: Cascading locks prevent deletion or mutation of factors and calculations referenced by published disclosures.
- **Cryptographic Audit Ledger**: Records every creation, classification, manual review, and approval action with immutable actor stamps.

### 5. Statutory Regulatory Disclosures (Phase 5)
- **Automated Entity Eligibility**: Evaluates corporate revenue, employee count, and geographic nexus to determine statutory filing requirements:
  - **California SB 253** (Climate Corporate Data Accountability Act)
  - **EU CSRD** (Corporate Sustainability Reporting Directive — ESRS E1 Climate Change)
  - **GHG Protocol Corporate Standard**
- **Audit-Grade PDF Generation**: Generates publication-ready disclosure documents with exact calculation footnotes and provenance hyperlinks.

### 6. Greenwashing & Anomaly Detection (Phase 6)
- **Statistical Ledger Auditing**:
  - **YoY Variance**: Flags unexplained YoY drops $>50\%$ or surges $>100\%$.
  - **Intensity Outliers**: Normalizes emissions per unit of activity and flags values deviating $\ge 3.0$ standard deviations from cohort means ($Z \ge 3.0$).
  - **Scope Completeness**: Enforces mandatory baseline scopes across multi-year cycles.
- **Narrative Claim Cross-Examination**: Groq LLM extracts claims from corporate CSR copy and cross-examines them against verified ledger totals to detect potential greenwashing.
- **Auditor Resolution**: Flags require auditor sign-off (`CONFIRMED` / `DISMISSED`) with documented rationale.

### 7. Executive Dashboard, Decarbonization Simulator & Supplier Outreach (Phase 7)
- **Executive ESG Analytics Dashboard**: Scope 1/2/3 breakdown, verified vs. estimated coverage metrics, top category hotspots, and multi-year emission trajectories.
- **Decarbonization Scenario Simulator**: Pure deterministic "what-if" abatement engine. Models 5 standard mitigation levers (Solar PPA, EV Fleet, Heat Pump Retrofits, Supply Chain Engagement, Travel Modal Shift) and computes the **Marginal Abatement Cost Curve (MACC)** ranked in $\$ / t\text{CO}_2e$.
- **Scope 3 Supplier Outreach Agent**: Automatically identifies missing primary supplier data, drafts customized outreach emails via Groq (with deterministic fallbacks), dispatches campaigns, and ingests primary supplier factors.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.12 / 3.11, FastAPI | Typed, async REST API framework |
| **Database** | Neon Serverless PostgreSQL / SQLite (test) | Relational ledger, JSONB metadata, foreign key constraints |
| **ORM & Migrations** | SQLAlchemy 2.0, Alembic | Async ORM, schema migrations |
| **Object Storage** | Backblaze B2 (prod) / MinIO (local) | S3-compatible immutable document store |
| **Worker Queue** | Celery, Redis | Asynchronous OCR and parsing workers |
| **LLM Provider** | Groq (`llama-3.3-70b-versatile`) | Scope classification, narrative check, email drafting |
| **Document Parsing**| `unstructured`, `pytesseract`, `pandas`, `openpyxl` | PDF utility bill OCR and ERP spreadsheet parsing |
| **PII Redaction** | Microsoft Presidio / Regex tokenizers | Pre-LLM data privacy sanitization |
| **Reporting** | ReportLab | Deterministic statutory PDF generation |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS | Responsive, modern web interface |
| **Client State** | TanStack Query v5 | Cache management and real-time ledger updates |
| **Testing** | `pytest`, `pytest-asyncio`, `pytest-cov`, `vitest` | Unit, API, and End-to-End integration testing |

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+ installed
- Node.js 18+ and npm installed
- Docker & Docker Compose (or local Redis & MinIO)
- Groq API Key ([console.groq.com](https://console.groq.com))
- Neon PostgreSQL connection string ([console.neon.tech](https://console.neon.tech))

### 2. Environment Setup

**Backend Configuration:**
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env`:
```ini
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xyz.neon.tech/greenlign?sslmode=require
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=greenlign-raw
```

**Frontend Configuration:**
```bash
cp frontend/.env.example frontend/.env
```
Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` is set.

---

### 3. Database Migrations & Factor Seeding

```bash
# Navigate to backend directory and activate virtual environment
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate | On Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# Run Alembic migrations to create tables:
alembic upgrade head

# Seed versioned EPA and DEFRA emission factors:
python -m app.seeds.factors
```

---

### 4. Running with Docker Compose

To start Redis, MinIO, Celery Worker, FastAPI backend, and Next.js frontend in one command:
```bash
docker compose -f infra/docker-compose.yml up --build
```

---

### 5. Running Standalone Services (Local Dev)

**Backend API:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Celery Worker:**
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

**Frontend App:**
```bash
cd frontend
npm install
npm run dev
```

- **Frontend Application:** [http://localhost:3000](http://localhost:3000)
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO Console:** [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)

---

## 🧪 Testing & Quality Gates

The Greenlign codebase is maintained with strict quality gates: zero lint errors, zero type errors, 100% test pass rate, and $\ge 85\%$ statement coverage.

### Run Backend Tests & Coverage:
```bash
cd backend
pytest --cov=app --cov-report=term-missing
```
*Current test suite: **232 passed** with **88%** total statement coverage.*

### Run Static Analysis & Type Checking:
```bash
cd backend
ruff check .
mypy app tests
```

### Build & Verify Frontend:
```bash
cd frontend
npm run build
```

---

## 🗺️ Application Routes

| Route | View | Description |
| :--- | :--- | :--- |
| `/` | **Home** | Overview of capabilities across all completed phases. |
| `/dashboard` | **Executive Dashboard** | Scope 1/2/3 summary, hotspots, coverage, and YoY trends. |
| `/simulator` | **Scenario Simulator** | Decarbonization what-if modeling and MACC ROI rankings. |
| `/supplier-outreach` | **Supplier Outreach** | Scope 3 data collection campaigns & Groq email generator. |
| `/review` | **Classification Review** | Human-in-the-loop review queue for low-confidence classifications. |
| `/audit-trail` | **Audit Provenance** | Sub-200ms end-to-end evidence trees and cryptographic logs. |
| `/disclosures` | **Regulatory Disclosures** | California SB 253, EU CSRD, and GHG Protocol PDF generation. |
| `/anomalies` | **Anomaly Center** | Statistical Z-score intensity outliers and greenwashing detection. |

---

## 🔒 Security & Data Privacy

1. **PII Tokenization**: Raw vendor account numbers, credit card tokens, and supplier names are scrubbed using Presidio before sending any text to LLM inference.
2. **Immutable Source Storage**: Raw source files are stored immutably in S3/MinIO and referenced strictly by SHA-256 hash.
3. **Database Integrity**: PostgreSQL foreign keys with `ON DELETE RESTRICT` protect all calculations and emission factors linked to filed regulatory disclosures.

---

## 📜 Release History

- `phase-0-complete`: Scaffolding, Data Model & Docker dev environment.
- `phase-1-complete`: Ingestion Pipeline (PDF OCR, CSV/XLSX parsing, Presidio PII).
- `phase-2-complete`: LLM Scope Classification & Human Review Queue.
- `phase-3-complete`: Deterministic Calculation Engine & Versioned Factor Matcher.
- `phase-4-complete`: Audit Provenance Evidence Trees & Governance Log.
- `phase-5-complete`: Statutory Regulatory Disclosures (CA SB 253, CSRD, GHG Protocol).
- `phase-6-complete`: Greenwashing & Statistical Anomaly Detection Engine.
- `phase-7-complete`: Executive ESG Dashboard, Decarbonization Simulator & Supplier Outreach Agent.

---

## 📄 License
Internal proprietary license. All rights reserved.
