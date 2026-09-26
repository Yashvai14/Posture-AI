# PostureAI — Architecture

PostureAI is a **posture screening and education tool**. It measures body-landmark geometry
in a photo and explains the result. It does not diagnose medical conditions.

## 1. System overview

```
┌──────────────────────────── Next.js 14 (App Router, strict TS) ────────────────────────────┐
│ AuthProvider · ProtectedRoute · pages compose components · TanStack Query · axios (Bearer) │
└───────────────┬─────────────────────────────────────────────────────────────────────────────┘
                │  HTTPS, Authorization: Bearer <JWT>   (NEXT_PUBLIC_API_URL)
┌───────────────▼──────────────────────── FastAPI ────────────────────────────────────────────┐
│ routers/  (thin: validation, auth dependency, HTTP mapping)                                 │
│    │                                                                                        │
│ services/ analysis_service ─► JobRunner (thread pool) ─► process_analysis(id)               │
│    │         │                                   ├─ posture/  (MediaPipe → geometry →       │
│    │         │                                   │             metrics → findings → score)  │
│    │         │                                   ├─ recommendations/ (curated library)      │
│    │         │                                   ├─ ai/ (Ollama, schema-validated,          │
│    │         │                                   │       deterministic fallback)            │
│    │         │                                   └─ reports/ (ReportLab PDF)                │
│    │      providers/ (Overpass + Nominatim, cache, normalise, dedupe)                       │
│    │      appointments/ (slot generation, booking, state machine)                          │
│    │      storage (private files) · audit log · rate limiter                                │
│ repositories/ (every patient-data query takes user_id)                                      │
└───────────────┬──────────────────────────────────────┬──────────────────────────────────────┘
                │ SQLAlchemy 2 + Alembic               │ local filesystem (STORAGE_DIR, private)
        ┌───────▼────────┐                     ┌────────▼────────┐        ┌──────────────┐
        │ PostgreSQL 16  │                     │ images, reports │        │ Ollama (opt.)│
        │ + PostGIS      │                     └─────────────────┘        └──────────────┘
        └────────────────┘
```

## 2. Database

All primary keys are UUIDs except `audit_logs`. Enumerations are `VARCHAR` + `CHECK`
constraints (portable, simple migrations). Schema is managed only by Alembic.

```
users 1───1 patient_profiles            (current, editable profile)
  │
  ├──* posture_analyses ──1 patient_snapshots      (profile + symptoms AS OF this analysis)
  │         ├──* posture_measurements              (metric, value, unit, confidence)
  │         ├──* posture_findings                  (code, severity, observation)
  │         ├──1 ai_recommendations                (validated explanation + curated plan, source)
  │         └──1 posture_reports                   (private PDF storage key)
  │
  ├──* appointments *──1 doctors *──1 providers
  │         │               └──* doctor_availability (weekday, start, end, slot length)
  │         └── optional link to a posture_analysis
  │
  └──* audit_logs

providers           OSM or manually onboarded facilities; geography(Point,4326) + GiST index;
                    unique (source, source_id); fetched_at / last_verified_at
provider_search_areas  cache of which areas were fetched from Overpass and when
```

Key constraints:

- `patient_snapshots.analysis_id` is unique → history always shows the data entered for *that* analysis.
- `posture_measurements (analysis_id, metric)` and `posture_findings (analysis_id, code)` are unique.
- `appointments` has two exclusion constraints (btree_gist):
  no overlapping active (`pending`/`confirmed`) appointments per doctor, and per patient.
- Check constraints on ages, heights, weights, confidences, weekdays, slot lengths, time ranges.

## 3. Posture analysis pipeline

```
upload ─► validate (size, extension, MIME, decode, pixel limit) ─► re-encode JPEG (EXIF/GPS stripped)
       ─► 202 Accepted {analysis_id, status: queued}
worker ─► image quality (resolution, brightness, contrast, sharpness)
       ─► MediaPipe Pose Landmarker (33 landmarks, visibility + presence)
       ─► pose checks: one person · full body in frame · landmarks visible · standing · person size
       ─► camera view: front / back / left side / right side  (oblique → rejected with guidance)
       ─► geometry → metrics (only those the view supports, each with confidence)
       ─► classifier (versioned heuristic thresholds) → findings with severity
       ─► alignment score (proprietary, not a health score)
       ─► annotated image (skeleton, reference lines, angles)
       ─► curated corrective plan + 4-week programme (deterministic)
       ─► Ollama explanation (structured facts in, JSON schema out, validated, safety-checked;
                              retry once; otherwise deterministic explanation, labelled)
       ─► PDF report
```

If the image is unsuitable the analysis ends with status `failed`, `failure_code=image_unsuitable`,
the individual quality checks, and a message telling the user how to retake the photo.
No measurements are produced from unsuitable images.

Metrics by view:

| View | Metric | Definition |
|---|---|---|
| Side | `head_forward_angle` | angle between the vertical through the shoulder and the shoulder→ear line |
| Side | `trunk_inclination` | angle between vertical and the hip→shoulder line (signed forward/back) |
| Side | `hip_line_deviation` | how far the hip sits off the shoulder→ankle line (signed forward/back) |
| Front/back | `shoulder_tilt` | angle of the shoulder line to horizontal (+ which side is higher) |
| Front/back | `hip_tilt` | angle of the hip line to horizontal |
| Front/back | `head_tilt` | angle of the ear line to horizontal |
| Front/back | `trunk_lateral_lean` | angle between vertical and the mid-hip→mid-shoulder line |

Thresholds live in `app/posture/classifier.py` (`THRESHOLDS`, `PIPELINE_VERSION`). They are
screening heuristics chosen for this product and **are not clinically validated**. Nothing
measures pelvic tilt, spinal curvature or scoliosis; the UI and prompts must not claim it.

## 4. AI (Ollama) boundary

The LLM never produces measurements, severities or exercises. It receives the measured facts
and the curated plan and returns `AIExplanation` (summary, what-this-may-mean, per-finding
explanation, lifestyle tips, follow-up guidance). Validation layers:

1. Ollama structured output (`format` = JSON schema), low temperature.
2. Pydantic model with length limits.
3. Semantic checks: finding codes must match the detected findings; diagnostic language
   ("you have …", named spinal/neurological diseases) is rejected.
4. One repair retry with the validation errors; then the deterministic explanation.

`ai_recommendations.source` is `ollama` or `rule_based` and the UI and PDF label it.

## 5. Security

- **Authentication:** bcrypt passwords (8–72 bytes), PyJWT HS256 access tokens with `sub` =
  user id, `iat`, `exp`, `type`. Sent only as `Authorization: Bearer`. Frontend keeps the token
  in `localStorage`; session is restored via `/auth/me` on load.
- **Authorization:** every repository function that reads patient data requires `user_id`.
  Foreign resources return 404 (existence is not revealed). Tested in `tests/test_isolation.py`.
- **Files:** stored under `STORAGE_DIR` with UUID names, never mounted as static files.
  Served only through `/api/analyses/{id}/image`, `/annotated-image`, `/report` after an ownership
  check, with `Cache-Control: no-store`. Uploads are re-encoded, which strips EXIF/GPS.
- **Configuration:** `SECRET_KEY` (≥32 chars) and `DATABASE_URL` (PostgreSQL only) are required;
  startup fails otherwise. `.env` is git-ignored; `.env.example` documents every setting.
- **Rate limiting:** in-process fixed window on login, registration and uploads.
- **Audit log:** registrations, logins (success and failure), analysis creation, file and report
  access, appointment changes.

## 6. Provider discovery (no fabricated data)

```
user location (browser geolocation or Nominatim place search)
  ─► PostGIS: is this area in provider_search_areas and fresher than PROVIDER_CACHE_DAYS?
       no ─► one Overpass query (healthcare/amenity tags, radius) ─► normalise ─► dedupe
             ─► upsert on (source, source_id) ─► record search area
  ─► ST_DWithin radius query ordered by ST_Distance ─► list + map
```

- Only fields present in OpenStreetMap are shown. Unnamed features are skipped. Nothing is invented.
- Records carry `source`, `source_id`, `source_url`, `fetched_at`; `last_verified_at` stays empty
  unless a person verifies the record. The UI says "Listed on OpenStreetMap — not verified by PostureAI"
  and shows the ODbL attribution.
- If Overpass is unavailable, cached results are returned with a notice; if there are none,
  the UI says no providers are available.
- **Booking** is only offered for doctors that were onboarded with real availability
  (`python -m app.cli create-doctor …`). OSM listings show contact details instead
  ("Call to book"), because booking them in PostureAI would not reach the real clinic.

## 7. Appointments

Weekly availability rules → slots in the clinic's time zone → UTC `starts_at/ends_at`.
Booking validates that the requested start is a generated, future, free slot, inserts in a
transaction, and maps an exclusion-constraint violation to HTTP 409. States:
`pending → confirmed → completed | no_show`, and `pending|confirmed → cancelled`.
Patients may cancel their own future appointments; other transitions are clinic/admin actions
(`python -m app.cli set-appointment-status`).

## 8. Background processing

`JobRunner` runs analysis jobs on a bounded thread pool and records progress in
`posture_analyses.status/stage`; the frontend polls `/api/analyses/{id}`. Jobs are idempotent
(results are written in one transaction per step and replaced on re-run), so queued or
interrupted jobs are re-submitted at startup. With more than one backend instance, replace the
runner with a Redis-backed queue (e.g. arq) — the interface is a single `submit()` call.
