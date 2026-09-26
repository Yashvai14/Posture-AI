# PostureAI — Project Context (for AI assistants)

> Paste this whole file into ChatGPT (or any LLM) before asking questions about the project.
> Do NOT paste `backend/.env` — it contains the JWT secret and DB credentials.

## 1. What it is

PostureAI is a full-stack web app for **AI posture screening**. The user flow:

1. User uploads a photo of their standing posture and enters profile info (name, age, gender, height, weight, symptoms).
2. Backend "analyzes" the image → detects posture problems (Forward Head, Text Neck, Uneven Shoulders, Anterior Pelvic Tilt, Mild Slouching) with a risk level (Low/Medium/High).
3. A **local LLM via Ollama** (llama3 by default) turns the problems + symptoms into findings, stretches, exercises and lifestyle tips. If Ollama is unreachable, a rule-based fallback produces the same JSON shape.
4. A **PDF report** is generated with ReportLab and can be downloaded.
5. User can find **nearby doctors** (Haversine distance, 30 km default) on a Leaflet/OpenStreetMap map and **book appointments**.
6. A **history page** lists past analyses with search.

Target region mentioned in docs: Nagpur, India (but seed data is New York).
Status: prototype / college-project level. Not a git repo yet. Appears to have been scaffolded by an AI IDE (README image points to a local `.gemini/antigravity-ide` path).

## 2. Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router), React 18, TypeScript (`strict: false`), Tailwind CSS 3, TanStack Query v5, axios, Leaflet 1.9 (loaded via `require` at runtime), lucide-react, framer-motion |
| Backend | FastAPI 0.110, Uvicorn, SQLAlchemy 2.0 (sync ORM), Pydantic v2 + pydantic-settings, python-jose (JWT HS256), bcrypt, httpx, Pillow, ReportLab |
| DB | PostgreSQL (`DATABASE_URL`), **auto-falls back to SQLite** `backend/postureai.db` if Postgres connection fails at startup. Tables created with `Base.metadata.create_all` (Alembic is in requirements but unused). |
| AI | Ollama HTTP API `POST {OLLAMA_URL}/api/generate` with `format: "json"`, 10 s timeout |
| External | OpenStreetMap Nominatim (doctor discovery), OSM tiles (map) |

Python 3.11, Node 18+. Backend on `http://localhost:8000`, frontend on `http://localhost:3000`.

## 3. Folder structure

```
Posture AI/
├── README.md
├── backend/
│   ├── .env                      # DATABASE_URL, SECRET_KEY, OLLAMA_URL, OLLAMA_MODEL, UPLOAD_DIR
│   ├── requirements.txt
│   ├── postureai.db              # SQLite fallback DB (currently only 4 seeded doctors)
│   ├── uploads/                  # uploaded images + uploads/reports/*.pdf
│   └── app/
│       ├── main.py               # FastAPI app, CORS (localhost:3000/3001), mounts /static/uploads, startup -> init_db
│       ├── core/config.py        # Settings (env vars, defaults)
│       ├── core/security.py      # create_access_token, bcrypt hash/verify
│       ├── db/session.py         # engine (Postgres -> SQLite fallback), SessionLocal, get_db
│       ├── db/init_db.py         # create_all + seed 4 mock NYC doctors
│       ├── models/models.py      # SQLAlchemy models
│       ├── schemas/schemas.py    # Pydantic schemas
│       ├── repositories/repository.py  # User/Analysis/Patient/Report/Doctor repositories (static methods)
│       ├── routers/
│       │   ├── deps.py           # get_current_user (Bearer header OR ?token= query param)
│       │   ├── auth.py           # register, token (login), me
│       │   ├── analysis.py       # upload + analyze pipeline, get analysis
│       │   ├── patients.py       # history with search
│       │   ├── doctors.py        # haversine search + discovery agent trigger
│       │   ├── appointments.py   # book, list
│       │   └── reports.py        # PDF download
│       └── services/
│           ├── cv_engine.py      # PostureCVEngine.analyze_image  (SIMULATED — see §7)
│           ├── ollama_service.py # OllamaService + rule-based fallback
│           ├── pdf_generator.py  # PDFReportGenerator (ReportLab)
│           └── discovery_agent.py# DoctorDiscoveryAgent (Nominatim scrape + mock fallback)
└── frontend/
    ├── package.json, tailwind.config.js, tsconfig.json (paths: "@/*" -> "./*")
    ├── lib/api.ts                # axios instance (baseURL hardcoded http://localhost:8000/api), token interceptor, authApi/analysisApi/doctorApi
    └── app/
        ├── layout.tsx            # nav + footer, loads Inter font + Leaflet CSS from CDN
        ├── providers.tsx         # QueryClientProvider
        ├── globals.css           # tailwind + .btn-primary/.btn-secondary/.btn-teal/.glass-nav
        ├── page.tsx              # marketing landing page (stats, features, FAQ)
        ├── dashboard/page.tsx    # profile form + image upload + results + PDF link
        ├── doctors/page.tsx      # geolocation, Leaflet map, doctor list, booking modal
        └── history/page.tsx      # searchable history cards + PDF links
```

There is no `components/` folder; each page is one large client component. No tests anywhere.

## 4. Data model (SQLAlchemy, all PKs are `String(36)` UUIDs)

- **User**: id, email (unique), hashed_password, full_name, created_at, updated_at → has many PatientHistory, PostureAnalysis, Appointment
- **PatientHistory**: id, user_id, age, gender, height (cm), weight (kg), symptoms, created_at — *one row per upload, but NOT linked to a specific analysis*
- **PostureAnalysis**: id, user_id, image_path, detected_problems (JSON list), risk_level, confidence_score, image_quality_score, created_at → has one Report
- **Report**: id, analysis_id, pdf_path, findings (text), recommendations (JSON: findings/stretches/exercises/lifestyle_tips), created_at
- **Doctor**: id, name, specialization, rating, experience_years, consultation_fee (Numeric), phone, email, latitude, longitude, address, availability (JSON `{days:[], slots:[]}`)
- **Appointment**: id, patient_id, doctor_id, appointment_date, appointment_time, status ("scheduled")

## 5. API (prefix `/api`, all except register/token need JWT)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | JSON `{email, password, full_name}` |
| POST | `/auth/token` | form-urlencoded `username`, `password` → `{access_token, token_type}`; JWT `sub` = email, 7-day expiry |
| GET | `/auth/me` | current user |
| POST | `/analysis/upload` | multipart: `file`, optional `name, age, gender, height, weight, symptoms` → returns `analysis_id, detected_problems, risk_level, confidence_score, metrics{ear_shoulder_angle, shoulder_tilt, hip_alignment}, findings, recommendations, report_id` |
| GET | `/analysis/{id}` | analysis + report summary |
| GET | `/patients/history?search=` | all analyses joined with user + latest PatientHistory |
| GET | `/doctors/search?latitude&longitude&radius_km=30` | haversine filter, sorted by distance; if 0 results, runs discovery agent then re-queries |
| POST | `/appointments/book` | JSON `{doctor_id, appointment_date, appointment_time}` |
| GET | `/appointments` | current user's appointments (with doctor) |
| GET | `/reports/{id}/download` | FileResponse PDF; checks ownership; frontend passes token as `?token=` |
| GET | `/health` | (no `/api` prefix) |
| static | `/static/uploads/...` | raw uploads dir, **no auth** |

## 6. Upload → report pipeline (`routers/analysis.py`)

1. Save file to `uploads/<uuid><ext>`.
2. `PostureCVEngine.analyze_image(path)` → problems, risk, confidence, quality, metrics.
3. If `name` given, overwrite `current_user.full_name`.
4. Insert PatientHistory row.
5. `await OllamaService.analyze_symptoms_and_posture(...)` → dict (LLM or fallback).
6. Insert PostureAnalysis row.
7. `PDFReportGenerator.generate_report(...)` → `uploads/reports/report_<analysis_id>.pdf` (includes first 2 doctors from DB as "recommended nearby specialists", regardless of location).
8. Insert Report row, return JSON.

Frontend auth: `dashboard/page.tsx` on mount calls `/auth/me`; if it fails it **auto-registers a random guest** (`guest_<rand>@postureai.com` / `password123`, name "John Doe") and logs in. Token stored in `localStorage`. The history and doctors pages do not do this, so they 401 if the dashboard wasn't visited first.

## 7. Important reality check — what is real vs. simulated

- **Posture detection is fake.** `cv_engine.py` only validates the image with Pillow, then does `random.seed(file_size)` and draws random angles (neck 10–35°, shoulder tilt 0–12°, hip 0–8°), confidence 0.85–0.98, quality 0.80–0.95. Same file size ⇒ same result; the image content is never inspected. Docstring says "in production, integrate MediaPipe Pose or a PyTorch model".
- Thresholds in code: Forward Head > 20°, Text Neck > 28°, Uneven Shoulders > 4°, Anterior Pelvic Tilt > 4.5°, none ⇒ "Mild Slouching". Risk High if ≥3 problems or neck > 28°, Medium if ≥2 or neck > 18°. README says neck > 15°; PDF says shoulder normal < 3° — inconsistent.
- Landing page stats ("98.4% Detection Accuracy", "10K+ images", "450+ doctors", "HIPAA-grade") are placeholder marketing, not measured.
- **Doctor data is largely fabricated.** Seeds are 4 fictional NYC doctors. The discovery agent gives OSM results random ratings/fees/phones/emails; if OSM returns nothing it creates 5 hardcoded "Nagpur" clinics at random offsets around *whatever* coordinates the user is at.
- Ollama call has a 10 s timeout, so on most machines llama3 generation times out and the rule-based fallback is used. LLM JSON output is not validated against the expected keys.

## 8. Known bugs / issues (verified or clearly visible in code)

Bugs:
1. **Upload without symptoms crashes with 500.** `analysis.py` puts `symptoms=None` into `patient_info`; `pdf_generator.py` does `patient_info.get("symptoms", "None")` → returns `None` → `Paragraph(None)` raises `AttributeError: 'NoneType' object has no attribute 'split'` (verified with ReportLab 4.4.4). The PostureAnalysis row is already committed, so an orphan analysis without a report is left behind. Same risk for `name` if it were ever None.
2. **`frontend/lib/api.ts` uses `float` as a TypeScript type** (`search: async (lat: float, lon: float, ...)`). `tsc --noEmit` fails with `Cannot find name 'float'`, so `next build` fails (dev mode still runs). Fix: `number`.
3. Nominatim is called with `lat`/`lon` query params, which Nominatim search ignores (needs `viewbox` + `bounded=1`), so results are global, often outside the radius; because they're still inserted, the mock fallback is skipped and the user can end up with 0 nearby doctors. 4 rapid requests also violate Nominatim's 1 req/s policy.
4. History shows `user.history[-1]` (the user's latest PatientHistory, unordered relationship) for every analysis, so older analyses display the wrong symptoms/age/etc. PatientHistory should have an `analysis_id` FK.
5. History/doctors pages 401 unless the dashboard ran first (guest auto-login lives only in dashboard).
6. `hip_alignment` is computed but not shown in the UI or PDF.
7. PDF and UI show fees with `$` while the target market is India.
8. Leaflet default marker icons usually 404 under Next.js bundling (icon URLs not configured); map instance isn't removed on unmount.

Security / privacy (contradicts the "HIPAA" claims):
- `/patients/history` returns **every user's** analyses, names, emails and symptoms to any logged-in user.
- `/analysis/{id}` has no ownership check.
- `/static/uploads` serves all uploaded photos and PDF reports with no auth.
- JWT passed in URL (`?token=`) for PDF downloads → leaks into browser history/server logs.
- Hardcoded guest password `password123`; default `SECRET_KEY` fallback in `config.py`.
- No upload size/type limits (extension taken from user's filename).
- CORS limited to localhost; API base URL hardcoded to `http://localhost:8000` in frontend (`lib/api.ts`, and PDF links in dashboard/history pages).

Code quality / cleanup:
- `@app.on_event("startup")` is deprecated (use lifespan); `datetime.utcnow()` deprecated.
- Unused deps: `alembic`, `passlib`, `react-leaflet`. `doctorApi.getAppointments` has no UI.
- No availability/double-booking validation on appointments; free-form time input ignores doctor's `availability.slots`.
- Doctor dict building is duplicated in `doctors.py`; no pagination; Haversine loops over all doctors in Python.
- No tests, no Docker, no git, no migrations.
- README architecture image uses a local `file:///C:/Users/...` path (broken for others).

## 9. How to run

```bash
# backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows (a .venv already exists)
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000, docs at /docs

# frontend
cd frontend
npm install
npm run dev                        # http://localhost:3000

# optional
ollama pull llama3 && ollama serve
```

`.env` keys: `DATABASE_URL`, `SECRET_KEY`, `OLLAMA_URL`, `OLLAMA_MODEL`, `UPLOAD_DIR`.

## 10. Obvious next steps (if asked "what should I build next")

1. Replace the simulated CV engine with real pose estimation (MediaPipe Pose / MoveNet): get ear, shoulder, hip keypoints → compute craniovertebral angle, shoulder tilt, pelvic tilt; return an annotated image with the skeleton overlay.
2. Fix the two crash bugs (§8.1, §8.2).
3. Scope `/patients/history` and `/analysis/{id}` to the current user (or add a doctor/admin role), protect uploads, stop passing tokens in URLs.
4. Proper login/register UI instead of the guest auto-account; shared auth hook for all pages.
5. Link PatientHistory to PostureAnalysis; add Alembic migrations.
6. Real doctor data (Nominatim with viewbox/bounded or Overpass API `amenity=clinic|hospital`, `healthcare=physiotherapist`) and drop fabricated ratings/phones.
7. Increase Ollama timeout / stream, validate LLM JSON with a Pydantic model.
8. Env-based API URL (`NEXT_PUBLIC_API_URL`), split pages into components, add tests, Docker Compose, git.

---

**My question for you:** <write your request here>
