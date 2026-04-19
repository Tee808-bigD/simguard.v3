# 🛡 SimGuard — Real-time SIM Swap Fraud Prevention

**Africa Ignite Hackathon 2026** | Prize: GBP 3,000 + MWC Kigali showcase

---

## Problem

Over **$500M lost annually** to SIM swap fraud in Africa. Current detection takes hours or days. Mobile money agents unknowingly process fraudulent transactions.

## Solution

SimGuard is an API-powered, AI-driven fraud detection system that:

- ✅ Detects SIM swaps in **real-time** using Nokia CAMARA APIs
- ✅ Verifies device integrity before high-value transactions
- ✅ Uses **Claude AI** as an agentic fraud decision engine
- ✅ Gives mobile money agents instant GO/BLOCK/FLAG guidance
- ✅ Live dashboard updates via WebSocket

---

## Architecture

```
React Dashboard (Vite + TailwindCSS + Recharts)
        │ REST + WebSocket
FastAPI Backend
  ├── Transaction Service
  ├── Fraud Detector (rule-based scoring)
  ├── Claude AI Engine (agentic decisions)
  └── CAMARA API Gateway
        ├── SIM Swap API
        ├── Device Swap API
        └── Number Verification API
SQLite (dev) / PostgreSQL (prod)
```

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3.11 · FastAPI · SQLAlchemy  |
| Frontend  | React 18 · Vite · TailwindCSS       |
| AI Engine | Anthropic Claude API                |
| CAMARA    | Nokia Network as Code (RapidAPI)    |
| Database  | SQLite (dev) · PostgreSQL (prod)    |
| Deploy    | Docker + docker-compose             |

---

## Quick Start

### 1. Clone & Configure

```bash
git clone <your-repo>
cd simguard
cp .env.example .env
# Edit .env — add your NAC_API_KEY and ANTHROPIC_API_KEY
```

### 2. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 4. Docker (full stack)

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/transactions` | Submit transaction for fraud check |
| GET | `/api/transactions` | List transactions |
| GET | `/api/transactions/{id}` | Get transaction detail |
| POST | `/api/fraud/check` | Quick fraud check (no DB write) |
| GET | `/api/fraud/alerts` | List fraud alerts |
| GET | `/api/dashboard/stats` | KPI statistics |
| GET | `/api/dashboard/timeline` | Hourly transaction chart data |
| GET | `/api/dashboard/risk-distribution` | Risk level breakdown |
| GET | `/api/verification/sim-status/{phone}` | SIM swap status |
| GET | `/api/verification/device-status/{phone}` | Device swap status |
| GET | `/api/verification/full-check/{phone}` | All CAMARA checks |
| WS | `/ws/alerts` | Real-time alert stream |

---

## Nokia Test Numbers (Sandbox)

| Number | Simulates |
|--------|-----------|
| `+99999991000` | SIM swap detected → **BLOCK** |
| `+99999991001` | Clean number → **APPROVE** |
| `+99999991002` | Device swap detected → **FLAG** |

---

## Fraud Detection Logic

### Risk Scoring (0–100)

```
SIM swap within 24h          +60 pts   ← Critical
SIM swap within 7d           +40 pts
Device swap detected         +30 pts
Amount > $1,000 equiv.       +30 pts
Amount > $500 equiv.         +20 pts
Composite: swap + high value +25 pts
Composite: swap + new recip  +20 pts
Both SIM + device swapped    +15 pts
```

### AI Decision Thresholds

| Decision | Condition |
|----------|-----------|
| BLOCK | score ≥ 60 OR SIM swap <24h + amount >$100 |
| FLAG_FOR_REVIEW | score 30–59 |
| APPROVE | score <30 AND no recent swap |

---

## Security Measures

- ✅ All secrets in `.env` only — never in code
- ✅ `.env` in `.gitignore` — cannot be committed
- ✅ Rate limiting: 60 req/min (global), 10/min (fraud endpoints)
- ✅ Max payload size: 1MB
- ✅ Phone number E.164 validation
- ✅ Currency whitelist (19 currencies)
- ✅ HTML/injection sanitization on all inputs
- ✅ CORS restricted to configured origins

---

## Currencies Supported

KES · UGX · TZS · ZMW · GHS · NGN · ZAR · RWF · MWK · ETB · XOF · USD · EUR · GBP · MZN · XAF · AOA · MAD · EGP

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NAC_API_KEY` | Nokia Network as Code (RapidAPI) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API |
| `DATABASE_URL` | SQLite or PostgreSQL URL |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) |
| `RATE_LIMIT_PER_MINUTE` | Global rate limit (default: 60) |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Auth endpoint limit (default: 10) |
| `MAX_PAYLOAD_SIZE` | Max request body in bytes (default: 1MB) |
| `APP_ENV` | `development` or `production` |

---

## Why SimGuard Wins

1. **3 CAMARA APIs** across 2 categories → maximum integration score
2. **Agentic Claude AI** → genuine innovation, bonus points
3. **$500M+ real-world problem** → strong impact narrative
4. **Full-stack working demo** → technical feasibility proven
5. **Agent portal** → directly addresses "agents unknowingly processing fraud"
6. **Real-time WebSocket** → impressive live demo
7. **Production-ready security** → scalability demonstrated
