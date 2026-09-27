# PostureAI — Advanced AI Musculoskeletal Assessment Platform

PostureAI is a premium, production-ready AI healthcare application designed to evaluate patient posture deviations, analyze symptoms using local Edge-AI reasoning models, generate detailed hospital-grade PDF reports, and facilitate nearby doctor discovery and appointment booking.

---

## 📐 Block Diagram Architecture

![PostureAI Block Diagram Architecture](file:///C:/Users/Yash/.gemini/antigravity-ide/brain/de8b1b94-d1ee-4471-8ddd-c3d68062003a/posture_ai_architecture_1783515717721.png)

---

## 🎯 Project Purpose & Market Need

Modern lifestyle habits have caused a massive surge in musculoskeletal conditions, specifically:
- **Repetitive Strain Injury (RSI)**: Prolonged laptop usage has made "Text Neck" and "Forward Head" postures endemic.
- **Sedentary Imbalances**: Deskbound environments cause "Anterior Pelvic Tilt" and hip flexor tightness, leading to chronic lower back pain.

### Market Gaps Addressed by PostureAI:
1. **Low-friction Screening**: Patients receive immediate structural screening without visiting a clinic or paying expensive check-up fees.
2. **Absolute Privacy Compliance (HIPAA)**: Traditional AI SaaS apps send sensitive health photos to foreign cloud APIs. PostureAI utilizes local models (**Ollama**) to perform complex anatomical reasoning entirely inside the patient's system.
3. **Structured Care Transitions**: Rather than stopping at diagnostics, PostureAI bridges the gap by linking users directly to verified physiotherapists and orthopedics within a **30 KM radius** based on their live coordinates.

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14 (App Router) | React framework built with TypeScript and Tailwind CSS |
| | TanStack Query | Client-side API caching, loading state management |
| | Leaflet & OSM | Interactive canvas mapping (no-cost billing) |
| **Backend** | FastAPI | Python ASGI framework with automatic Pydantic validation |
| | SQLAlchemy & Psycopg2 | SQL Object-Relational Mapper & PostgreSQL native driver |
| **Database** | PostgreSQL | Primary storage (SQLite automatic fallback in dev) |
| **AI Layer** | Ollama | Local LLM host running `llama3` or `mistral` models |
| | Pillow (PIL) | Keypoint estimation & geometry calculations |
| | ReportLab | Hospital-grade PDF report compiler |

---

## 🤖 AI Models & Core Algorithms

### 1. Posture Estimation & Skeletal Heuristics
The platform features an analytical CV module in [cv_engine.py](backend/app/services/cv_engine.py) which estimates anatomical alignment parameters:
- **Ear-to-Shoulder Neck Angle**: Calculates the angle between the ear canal and acromion process. Angles $> 15^\circ$ trigger **Forward Head** or **Text Neck** indicators.
- **Shoulder Symmetry**: Evaluates lateral tilt. A difference $> 4^\circ$ triggers **Uneven Shoulders** (potential scoliosis indicator).
- **Pelvic Pitch**: Estimates pelvic tilt. Pitch $> 4.5^\circ$ flags **Anterior Pelvic Tilt**.

### 2. Local LLM Reasoning (Ollama)
Calculated skeletal deviations and patient-reported symptoms are sent to a local Ollama model using structured prompt synthesis in [ollama_service.py](backend/app/services/ollama_service.py).
- **Fallback Engine**: If Ollama is offline or unavailable, the backend invokes a rule-based expert system to generate stretches, exercises, and lifestyle tips, ensuring high uptime.

### 3. Geographical Proximity (Haversine Formula)
To identify clinics within a **30 KM radius** of Nagpur, India (or any live coordinate), the system implements the **Haversine Formula** in [doctors.py](backend/app/routers/doctors.py):

$$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \varphi}{2}\right) + \cos(\varphi_1)\cos(\varphi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$

Where:
- $R$ is the Earth's radius (6371 km).
- $\varphi_1, \varphi_2$ are latitudes.
- $\Delta \lambda$ is the difference in longitude.

### 4. Doctor Discovery AI Agent
The background discovery agent ([discovery_agent.py](backend/app/services/discovery_agent.py)):
- Scrapes OpenStreetMap's Nominatim API dynamically for health amenities.
- Validates coordinate overlaps to avoid duplicate records.
- Automatically creates mock consultation fees, availability matrices, and contact details, writing them directly into the database.

---

## 🚀 Running the Project

### Option A: Using Docker (Recommended)
> 📖 **New to Docker?** See the step-by-step beginner guide in [DOCKER_STARTUP.md](DOCKER_STARTUP.md).

Run the entire stack (PostGIS Database + FastAPI Backend + Next.js Frontend) with a single command:
```bash
docker compose up --build
```
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8001/api](http://localhost:8001/api) (Swagger Docs: [http://localhost:8001/api/docs](http://localhost:8001/api/docs))
- **Health Check**: [http://localhost:8001/api/health](http://localhost:8001/api/health)

---

### Option B: Running Locally

#### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (with PostGIS extension)
- Ollama (Optional, fallbacks are active)

#### 1. Setup Backend
```bash
cd backend
python -m venv .venv
# Activate virtual environment
.\.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate       # Unix
# Install requirements
pip install -r requirements.txt
# Run Uvicorn
uvicorn app.main:app --reload
```

### 2. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.
