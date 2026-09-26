# PostureAI — Audit of the original prototype (2026-09-27)

Snapshot of the audited code: `.snapshots/original-prototype-2026-09-27.zip`
Snapshot of the audited database: `.snapshots/postureai-original-2026-09-27.sql`

## 1. Architecture assessment

The prototype was a single FastAPI app plus a Next.js 14 app:

```
Next.js pages (one large client component each)
   │ axios, token in localStorage, also passed as ?token= in URLs
   ▼
FastAPI routers ──► repositories ──► SQLAlchemy models (create_all, SQLite fallback)
   │
   ├─ cv_engine.py        random numbers seeded by file size
   ├─ ollama_service.py   free-form JSON from the LLM, saved without validation
   ├─ pdf_generator.py    ReportLab
   └─ discovery_agent.py  Nominatim + generated doctors
```

Biggest weaknesses, in order of impact:

1. **The core feature was simulated.** `cv_engine.py` never looked at the photo. It called
   `random.seed(os.path.getsize(path))` and drew random angles. Two different photos with the
   same byte size produced identical "findings".
2. **Health data was not isolated between users.** `/patients/history` returned every user's
   name, email, age, symptoms and findings to any logged-in user. `/analysis/{id}` had no
   ownership check. `/static/uploads` served every photo and PDF with no authentication.
3. **Fabricated healthcare data.** Four fictional seeded doctors; the discovery agent invented
   ratings, fees, phone numbers and e-mail addresses, and created hard-coded "Nagpur" clinics
   at random offsets around *any* user location.
4. **Broken data model.** `PatientHistory` was not linked to an analysis; history showed the
   user's latest profile against every past analysis.
5. **Unvalidated LLM output** was saved and rendered directly.

## 2. What worked (and was kept or reused)

| Area | Status | Decision |
|---|---|---|
| FastAPI + SQLAlchemy + Pydantic layering (routers → repositories) | Worked | Kept the layering, rewrote contents |
| bcrypt password hashing | Worked | Kept |
| ReportLab PDF generation and colour palette | Worked (with a crash bug) | Rebuilt the report, kept palette |
| Haversine formula | Correct | Kept as a pure helper for tests; search now uses PostGIS |
| Tailwind theme tokens (medical blue / teal / emerald) | Good | Kept |
| TanStack Query + axios | Fine | Kept, restructured |
| Rule-based fallback content idea | Useful | Replaced by a curated, reviewed exercise library |

## 3. What was simulated

- Posture measurements, confidence score and image-quality score (`random.uniform`).
- Doctor records (seed data + generated ratings/fees/phones/emails).
- Landing page claims: "98.4% Detection Accuracy", "10K+ Images Analyzed", "450+ Doctors
  Connected", "HIPAA-grade privacy" — none measured or substantiated.
- "Pelvic tilt": no landmark in the prototype (or in MediaPipe) can measure it from a photo.

## 4. What was broken (verified)

| # | Problem | Evidence |
|---|---|---|
| B1 | Upload without symptoms → HTTP 500 | `patient_info.get("symptoms","None")` returns `None`; `Paragraph(None)` raises `AttributeError` (reproduced with ReportLab) |
| B2 | `next build` fails | `lib/api.ts` used `float` as a TypeScript type (`tsc --noEmit` error TS2552) |
| B3 | Nominatim search ignored location | `lat`/`lon` are not Nominatim search parameters; results were global |
| B4 | History showed wrong symptoms/age for older analyses | `user.history[-1]` used for every row |
| B5 | History/Doctors pages returned 401 unless Dashboard was opened first | guest auto-login only lived in the Dashboard |
| B6 | Ollama nearly always timed out | 10 s timeout for a full generation |
| B7 | Leaflet default marker icons 404 under Next.js; map never removed on unmount | `doctors/page.tsx` |
| B8 | Thresholds inconsistent between README (15°), code (20°) and PDF (3°) | — |

## 5. What was insecure

| # | Issue | Severity |
|---|---|---|
| S1 | Cross-user access to health data (`/patients/history`, `/analysis/{id}`) | Critical |
| S2 | Public, unauthenticated file serving of body photos and reports (`/static/uploads`) | Critical |
| S3 | JWT in query strings (`?token=`) → browser history, proxy and server logs | High |
| S4 | Hard-coded default `SECRET_KEY`; silent SQLite fallback | High |
| S5 | Automatic guest accounts with the shared password `password123` | High |
| S6 | No upload validation (size, type, decompression bombs); EXIF (incl. GPS) kept | High |
| S7 | `python-jose` 3.3.0 (CVE-2024-33663/33664), `python-multipart` 0.0.9 (CVE-2024-53981), Pillow 10.2 (CVE-2024-28219), Starlette 0.36 (CVE-2024-47874) | High |
| S8 | No rate limiting on login | Medium |
| S9 | JWT subject was the e-mail address (changes break tokens; leaks PII in token) | Low |

## 6. Prioritized implementation plan

| Priority | Item | Phase |
|---|---|---|
| P0 | Ownership enforcement in repositories; 404 for foreign resources | 2 |
| P0 | Private file storage + authenticated file endpoints; strip EXIF | 2 |
| P0 | Bearer-only JWT (PyJWT), required secrets, no SQLite fallback | 2 |
| P0 | Real register/login/logout, session restore, protected routes | 2 |
| P0 | Fix B1, B2 | 2 |
| P0 | Upgrade vulnerable dependencies | 2 |
| P0 | Replace random CV engine with MediaPipe Pose + quality gate | 4 |
| P0 | Remove fabricated doctors and fake marketing claims | 7 / UI |
| P1 | PostgreSQL + Alembic schema: analysis-scoped patient snapshot, measurements, findings | 3 |
| P1 | Structured, validated LLM output with retry + deterministic fallback | 5 |
| P1 | Background analysis jobs with progress stages | 5 / 10 |
| P1 | Professional PDF (annotated image, ₹, disclaimer, red flags) | 6 |
| P1 | Provider discovery from OpenStreetMap (Overpass) with caching and attribution; PostGIS radius search | 7 |
| P1 | Slot-based booking with DB-level double-booking prevention | 8 |
| P1 | Pytest suite incl. cross-user isolation tests | all |
| P2 | Progress tracking (score + metric trends per camera view) | 9 |
| P2 | Component-based frontend, strict TypeScript, env-based API URL | 2 / UI |
| P2 | Docker Compose, CI workflow, Playwright E2E | 10 |
| P3 | Redis-backed queue + distributed rate limiting (needed only with >1 backend instance) | future |
| P3 | Clinical validation study of posture thresholds; clinician review of exercise library | future |
| P3 | Provider onboarding portal (so clinics can manage their own availability) | future |
