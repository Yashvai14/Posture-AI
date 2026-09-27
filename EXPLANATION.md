# PostureAI — Comprehensive Architectural & Clinical Engineering Guide

> **Document Version:** 2.0.0  
> **Target Audience:** Engineers, Clinical Reviewers, AI Researchers, and Contributors  
> **Status:** Production Specification  

---

## Table of Contents
1. [Executive Summary & System Purpose](#1-executive-summary--system-purpose)
2. [End-to-End System Architecture & Data Flow](#2-end-to-end-system-architecture--data-flow)
3. [The AI & Computer Vision Model (MediaPipe BlazePose)](#3-the-ai--computer-vision-model-mediapipe-blazepose)
   - [3.1 Model Foundation & Pipeline Topology](#31-model-foundation--pipeline-topology)
   - [3.2 The 33 Full-Body Anatomical Landmarks](#32-the-33-full-body-anatomical-landmarks)
   - [3.3 2D Coordinate Space vs. Metric 3D Depth ($z$)](#33-2d-coordinate-space-vs-metric-3d-depth-z)
4. [Image Quality & Biomechanical Pre-Flight Checks](#4-image-quality--biomechanical-pre-flight-checks)
   - [4.1 Photometric Quality Checks](#41-photometric-quality-checks)
   - [4.2 Postural & Geometric Suitability](#42-postural--geometric-suitability)
   - [4.3 Group Detection Rejection](#43-group-detection-rejection)
5. [Camera Perspective & View Classification](#5-camera-perspective--view-classification)
   - [5.1 3D Anatomical Yaw Calculation](#51-3d-anatomical-yaw-calculation)
   - [5.2 View Resolution Logic](#52-view-resolution-logic)
6. [Biomechanical Metrics & Mathematical Formulas](#6-biomechanical-metrics--mathematical-formulas)
   - [6.1 Frontal / Coronal Plane Metrics](#61-frontal--coronal-plane-metrics)
   - [6.2 Lateral / Sagittal Plane Metrics](#62-lateral--sagittal-plane-metrics)
7. [Posture Deviation Classification & Scoring Engine](#7-posture-deviation-classification--scoring-engine)
   - [7.1 Classification Rules & Thresholds](#71-classification-rules--thresholds)
   - [7.2 The 0–100 Alignment Score Algorithm](#72-the-0100-alignment-score-algorithm)
   - [7.3 Clinical Risk Categorization](#73-clinical-risk-categorization)
8. [Corrective Plan & Clinical Recommendation Engine](#8-corrective-plan--clinical-recommendation-engine)
   - [8.1 Curated Physical Therapy Exercise Library](#81-curated-physical-therapy-exercise-library)
   - [8.2 Dual-Layer LLM / Rule-Based Explanation Engine](#82-dual-layer-llm--rule-based-explanation-engine)
9. [Automated PDF Clinical Report Generation](#9-automated-pdf-clinical-report-generation)
10. [Geospatial Provider Discovery (PostGIS & OpenStreetMap)](#10-geospatial-provider-discovery-postgis--openstreetmap)
11. [Glossary of Terms, Medical Concepts & Technical Definitions](#11-glossary-of-terms-medical-concepts--technical-definitions)

---

## 1. Executive Summary & System Purpose

**PostureAI** is an automated, non-invasive biomechanical screening and clinical guidance platform. It enables individuals to upload a single photographic image of their natural standing posture and receive:

1. **Objective Computer Vision Measurements**: Mathematically quantified postural angles (e.g., craniovertebral head tilt, shoulder obliquity, pelvic unleveling, trunk inclination).
2. **Clinical Deviation Detection**: Rule-based screening for common musculoskeletal patterns (such as Forward Head Posture, Kyphotic Trunk Inclination, Swayback, and Asymmetrical Shoulder Elevating).
3. **Evidence-Based Corrective Programs**: Curated mobility routines, therapeutic stretches, ergonomic adjustments, and low-intensity strength exercises tailored to the detected deviations.
4. **Medical-Grade PDF Documentation**: Standardized screening reports generated with vector charts and anatomical summaries for healthcare consultations.
5. **Local Healthcare Provider Discovery**: PostGIS-powered geospatial discovery connecting patients with local physiotherapists, orthopaedists, and chiropractors within a 30–50 km radius.

> **Clinical Disclaimer:** PostureAI is designed as an educational and screening support tool. It does not replace a comprehensive, in-person clinical examination by a licensed medical practitioner, physiatrist, or physical therapist.

---

## 2. End-to-End System Architecture & Data Flow

PostureAI is architected around clean boundaries between **client presentation**, **synchronous REST routing**, **asynchronous task execution**, **spatial database persistence**, and **local AI inference**.

```
[User Browser / Next.js 14]
         │
         │  1. Multipart Upload (Photo + Profile Snapshot)
         ▼
[FastAPI Gateway (Uvicorn / Docker)]
         │
         │  2. Photometric & File Validation (MIME, Magic Bytes, Resolution)
         │  3. Save Original to Private File Storage (/app/storage/originals)
         │  4. Enqueue Job & Persist State in PostGIS Database
         ▼
[Asynchronous Pipeline Runner (Job Workers)]
         │
         ├───► A. MediaPipe Tasks Pose Landmarker (33 Full-Body 3D Keypoints)
         │
         ├───► B. Quality & Perspective Classifier (Yaw, Lighting, Sharpness)
         │
         ├───► C. Biomechanical Geometry Engine (Trigonometric Angle Extraction)
         │
         ├───► D. Postural Rule Classifier (Severity & Alignment Score 0-100)
         │
         ├───► E. Recommendation Engine (Curated Library + Local Ollama LLM)
         │
         ├───► F. Pose Annotator (Renders Skeleton & Angle Arcs to JPG)
         │
         └───► G. ReportLab Engine (Compiles Vector PDF Clinical Report)
         │
         ▼
[PostGIS / PostgreSQL Database & Storage]
         │
         │  5. Status Updated to "completed"
         ▼
[Client State & Dashboard Polling]
         │  6. Renders Diagnostic Metrics, Visual Diagrams, & PDF Download Link
```

---

## 3. The AI & Computer Vision Model (MediaPipe BlazePose)

### 3.1 Model Foundation & Pipeline Topology
PostureAI uses the **Google MediaPipe Pose Landmarker** model (`pose_landmarker_full.task`), built on the **BlazePose GHUM 3D** architecture.

- **Two-Stage Pipeline:**
  1. **Detector Network (BlazeDetector):** Scans the input image to identify the human bounding box based on face/torso alignment. It establishes a region-of-interest (ROI) frame rotated to match the body's vertical axis.
  2. **Landmarker Network (GHUM 3D Regressor):** Operates on the aligned ROI to predict 33 3D landmark points, visibility flags, and presence likelihood scores simultaneously.
- **Inference Mode:** Synchronous single-image execution (`RunningMode.IMAGE`).
- **Group Rejection Capability:** Configured with `num_poses=2`. If more than one person is detected in the frame, the system explicitly rejects the image to prevent misattributing body landmarks between multiple individuals.

### 3.2 The 33 Full-Body Anatomical Landmarks

```
                     0  (Nose)
                 1 ──┼── 4   (Eyes: Inner)
                 2 ──┼── 5   (Eyes)
                 3 ──┼── 6   (Eyes: Outer)
                 7 ──┴── 8   (Ears)
                     │
                 9 ──┴── 10  (Mouth Corners)
                     │
        11 ──────────┴────────── 12  (Shoulders)
        │                         │
        13 (Elbow)               14 (Elbow)
        │                         │
        15 (Wrist)               16 (Wrist)
        ├── 17, 19, 21 (Hand)    ├── 18, 20, 22 (Hand)
        │                         │
        23 ────────────────────── 24  (Hips / Pelvis)
        │                         │
        25 (Knee)                26 (Knee)
        │                         │
        27 (Ankle)               28 (Ankle)
        │                         │
        29 (Heel)                30 (Heel)
        │                         │
        31 (Foot Index / Toe)    32 (Foot Index / Toe)
```

### 3.3 2D Coordinate Space vs. Metric 3D Depth ($z$)
MediaPipe outputs two representations for every landmark point:
1. **Normalized Image Coordinates $(x, y)$:** Values mapped from $0.0$ to $1.0$, scaled by image width $W$ and image height $H$.
2. **Metric Depth Coordinate ($z$):** Represents landmark depth relative to the midpoint of the hips, with positive $z$ values pointing into the screen (away from the camera) and negative $z$ values pointing toward the camera.

---

## 4. Image Quality & Biomechanical Pre-Flight Checks

Before biomechanical measurements are calculated, the input image must pass a series of **Photometric** and **Anatomical Suitability** checks. Images that fail are halted with informative guidance rather than producing erroneous angles.

### 4.1 Photometric Quality Checks
1. **Resolution Threshold:** Shorter side must be $\ge 360\text{ px}$.
2. **Brightness Check:**
   $$\text{Brightness} = \frac{1}{WH} \sum_{x,y} \left(0.299R + 0.587G + 0.114B\right)$$
   - Acceptable range: $35.0 \le \text{Brightness} \le 225.0$.
3. **Contrast Check:** Standard deviation of grayscale pixel intensities must satisfy $\sigma \ge 18.0$.
4. **Sharpness Check:** Computed using discrete Laplace convolutions:
   $$\nabla^2 f = \frac{\partial^2 f}{\partial x^2} + \frac{\partial^2 f}{\partial y^2}$$
   - Images with sharpness variance $< 8.0$ are rejected as motion-blurred.

### 4.2 Postural & Geometric Suitability
1. **Standing Posture Validation:**
   - Both upper legs (hip-to-knee) must be within $30^\circ$ of vertical:
     $$\theta_{\text{leg}} = \arctan\left(\frac{|\Delta x|}{|\Delta y|}\right) \le 30.0^\circ$$
   - Trunk segment (midpoint of hips to midpoint of shoulders) must be within $35^\circ$ of vertical.
   - Prevents seated, lying down, or crouched photos from being analyzed as standing posture.
2. **Vertical Body Proportion:** Vertical distance from nose to ankles must occupy at least $45\%$ of the photo's height:
   $$\frac{y_{\text{ankle}} - y_{\text{nose}}}{H} \ge 0.45$$
3. **Frame Margin & Completeness:** Head, shoulders, hips, knees, and ankles must be within the frame (with a maximum margin of $2\%$). If ankles or ears are cropped off, the check flags missing anatomical points.

### 4.3 Group Detection Rejection
If the detector finds 2 or more individuals in the photo, the analysis immediately stops:
`"Multiple people detected. Please upload a photo containing only the patient."`

---

## 5. Camera Perspective & View Classification

Accurate posture evaluation depends on the camera view. A lateral angle (like craniovertebral angle) cannot be measured from a frontal photo, and shoulder height asymmetry cannot be measured from the side.

### 5.1 3D Anatomical Yaw Calculation
The system calculates body rotation relative to the camera (Yaw) using the 3D depth difference between bilateral anatomical pairs:

$$\Delta z_{\text{shoulder}} = z_{\text{left\_shoulder}} - z_{\text{right\_shoulder}}$$
$$\Delta x_{\text{shoulder}} = x_{\text{left\_shoulder}} - x_{\text{right\_shoulder}}$$
$$\text{Yaw}_{\text{shoulder}} = \left| \arctan2\left(\Delta z_{\text{shoulder}}, \Delta x_{\text{shoulder}}\right) \right| \times \frac{180^\circ}{\pi}$$

$$\Delta z_{\text{hip}} = z_{\text{left\_hip}} - z_{\text{right\_hip}}$$
$$\Delta x_{\text{hip}} = x_{\text{left\_hip}} - x_{\text{right\_hip}}$$
$$\text{Yaw}_{\text{hip}} = \left| \arctan2\left(\Delta z_{\text{hip}}, \Delta x_{\text{hip}}\right) \right| \times \frac{180^\circ}{\pi}$$

$$\text{Yaw}_{\text{body}} = \frac{\text{Yaw}_{\text{shoulder}} + \text{Yaw}_{\text{hip}}}{2}$$

### 5.2 View Resolution Logic
- **Frontal / Coronal View ($\text{Yaw} \le 30.0^\circ$):**
  - If Nose $z < \frac{z_{\text{left\_ear}} + z_{\text{right\_ear}}}{2}$, Classified as **`FRONT` (Anterior)**.
  - If Nose is behind ears or occluded, Classified as **`BACK` (Posterior)**.
- **Lateral / Sagittal View ($\text{Yaw} \ge 55.0^\circ$):**
  - If Left side depth is closer to camera, Classified as **`SIDE_LEFT` (Lateral Left)**.
  - If Right side depth is closer to camera, Classified as **`SIDE_RIGHT` (Lateral Right)**.
- **Oblique / Diagonal Angle ($30.0^\circ < \text{Yaw} < 55.0^\circ$):**
  - The photo is **rejected** because oblique angles distort both frontal tilt and lateral forward-head calculations.

---

## 6. Biomechanical Metrics & Mathematical Formulas

PostureAI calculates specific sets of metrics depending on the detected camera perspective.

### 6.1 Frontal / Coronal Plane Metrics

```
               (Left Ear) •────────• (Right Ear)      ──► Head Tilt Angle
                           \      /
     (Left Shoulder) •──────\────/──────• (Right Shoulder) ──► Shoulder Tilt Angle
                     │       \  /       │
                     │        ••        │ (Mid-Shoulder)
                     │        │         │
                     │        │ (Trunk) │             ──► Sideways Trunk Lean
                     │        │         │
                     │        •• (Mid-Hip)
        (Left Hip)   •────────┴─────────• (Right Hip)      ──► Hip Tilt Angle
```

#### 1. Shoulder Tilt Angle ($\theta_{\text{shoulder}}$)
Measures shoulder height asymmetry relative to horizontal:
$$\theta_{\text{shoulder}} = \left| \arctan2\left(y_{\text{left\_shoulder}} - y_{\text{right\_shoulder}}, x_{\text{left\_shoulder}} - x_{\text{right\_shoulder}}\right) \right| \times \frac{180^\circ}{\pi}$$

#### 2. Hip Tilt Angle ($\theta_{\text{hip}}$)
Measures pelvic unleveling across the anterior superior iliac spine (ASIS) axis:
$$\theta_{\text{hip}} = \left| \arctan2\left(y_{\text{left\_hip}} - y_{\text{right\_hip}}, x_{\text{left\_hip}} - x_{\text{right\_hip}}\right) \right| \times \frac{180^\circ}{\pi}$$

#### 3. Head Tilt Angle ($\theta_{\text{head}}$)
Quantifies lateral head roll relative to horizontal:
$$\theta_{\text{head}} = \left| \arctan2\left(y_{\text{left\_ear}} - y_{\text{right\_ear}}, x_{\text{left\_ear}} - x_{\text{right\_ear}}\right) \right| \times \frac{180^\circ}{\pi}$$

#### 4. Sideways Trunk Lean ($\theta_{\text{trunk\_lateral}}$)
Evaluates lateral spinal deviation between the shoulder center and hip center relative to vertical:
$$P_{\text{mid\_shoulder}} = \left(\frac{x_{\text{L.Sh}} + x_{\text{R.Sh}}}{2}, \frac{y_{\text{L.Sh}} + y_{\text{R.Sh}}}{2}\right)$$
$$P_{\text{mid\_hip}} = \left(\frac{x_{\text{L.Hip}} + x_{\text{R.Hip}}}{2}, \frac{y_{\text{L.Hip}} + y_{\text{R.Hip}}}{2}\right)$$
$$\theta_{\text{trunk\_lateral}} = \left| \arctan2\left(|x_{\text{mid\_shoulder}} - x_{\text{mid\_hip}}|, |y_{\text{mid\_hip}} - y_{\text{mid\_shoulder}}|\right) \right| \times \frac{180^\circ}{\pi}$$

---

### 6.2 Lateral / Sagittal Plane Metrics

```
             (Ear) •
                    \
                     \  (Head Forward Angle)
                      \
        (Shoulder) •───| (Vertical Reference Line)
                   │
                   │ (Trunk Inclination)
                   │
             (Hip) •
                    \
                     \ (Hip Line Deviation / Swayback)
                      \
             (Ankle) •
```

#### 1. Head Forward Angle / Craniovertebral Deviation ($\theta_{\text{head\_forward}}$)
Measures forward translation of the external auditory meatus (ear) relative to the vertical plumb line through the acromion process (shoulder):
$$\theta_{\text{head\_forward}} = \text{sign}_{\text{facing}} \times \arctan2\left(x_{\text{ear}} - x_{\text{shoulder}}, y_{\text{shoulder}} - y_{\text{ear}}\right) \times \frac{180^\circ}{\pi}$$
- Positive values indicate forward head posture (anterior head translation).

#### 2. Trunk Inclination ($\theta_{\text{trunk\_inclination}}$)
Measures the sagittal angle of the torso segment connecting shoulder to hip relative to vertical:
$$\theta_{\text{trunk}} = \text{sign}_{\text{facing}} \times \arctan2\left(x_{\text{shoulder}} - x_{\text{hip}}, y_{\text{hip}} - y_{\text{shoulder}}\right) \times \frac{180^\circ}{\pi}$$
- Positive: Forward trunk lean (anterior lean).
- Negative: Backward trunk lean (posterior lean).

#### 3. Hip Line Deviation / Swayback ($\Delta_{\text{hip\_deviation}}$)
Quantifies anterior or posterior pelvic shift relative to the primary gravitational axis (the line connecting the shoulder to the ankle):
$$\vec{u} = P_{\text{ankle}} - P_{\text{shoulder}}$$
$$\text{Offset} = \frac{(x_{\text{hip}} - x_{\text{shoulder}})u_y - (y_{\text{hip}} - y_{\text{shoulder}})u_x}{\|\vec{u}\|}$$
- Interior knee-hip-shoulder angle deviation:
$$\text{Deviation} = 180^\circ - \angle(P_{\text{shoulder}}, P_{\text{hip}}, P_{\text{ankle}})$$
- Positive values indicate the pelvis is translated forward (swayback posture).

---

## 7. Posture Deviation Classification & Scoring Engine

### 7.1 Classification Rules & Thresholds

| Finding Code | Clinical Deviation Pattern | Metric Applied | Mild Threshold | Moderate Threshold | Pronounced Threshold | Directionality |
|---|---|---|---|---|---|---|
| `forward_head` | Forward head posture (Text Neck) | `head_forward_angle` | $\ge 15.0^\circ$ | $\ge 25.0^\circ$ | $\ge 35.0^\circ$ | $+1$ (forward) |
| `trunk_forward_lean` | Anterior trunk lean | `trunk_inclination` | $\ge 6.0^\circ$ | $\ge 10.0^\circ$ | $\ge 15.0^\circ$ | $+1$ (forward) |
| `trunk_backward_lean`| Posterior trunk lean | `trunk_inclination` | $\ge 6.0^\circ$ | $\ge 10.0^\circ$ | $\ge 15.0^\circ$ | $-1$ (backward) |
| `hips_forward` | Swayback / Anterior pelvic shift | `hip_line_deviation` | $\ge 6.0^\circ$ | $\ge 10.0^\circ$ | $\ge 15.0^\circ$ | $+1$ (forward) |
| `uneven_shoulders` | Shoulder elevation asymmetry | `shoulder_tilt` | $\ge 2.5^\circ$ | $\ge 5.0^\circ$ | $\ge 8.0^\circ$ | Absolute ($0$) |
| `uneven_hips` | Pelvic unleveling | `hip_tilt` | $\ge 3.0^\circ$ | $\ge 5.0^\circ$ | $\ge 8.0^\circ$ | Absolute ($0$) |
| `head_tilt` | Lateral cervical tilt | `head_tilt` | $\ge 4.0^\circ$ | $\ge 8.0^\circ$ | $\ge 12.0^\circ$ | Absolute ($0$) |
| `lateral_trunk_lean` | Lateral spinal tilt | `trunk_lateral_lean` | $\ge 3.0^\circ$ | $\ge 6.0^\circ$ | $\ge 10.0^\circ$ | Absolute ($0$) |

### 7.2 The 0–100 Alignment Score Algorithm
The overall **Posture Alignment Score** is normalized from $0.0$ to $100.0$.
It starts at a perfect baseline of $100.0$ and subtracts weighted penalties based on metric deviations:

$$\text{Alignment Score} = 100.0 - \sum_{i \in \text{Metrics}} W_i \times \text{Penalty}_i$$

1. **Threshold Penalties:**
   Penalties start at $60\%$ of the mild threshold ($0.6 \times T_{\text{mild}}$) so subtle improvements are visible over time:
   $$\text{Penalty}_i = \begin{cases} 
   0 & \text{if } V_i < 0.6 T_{\text{mild}} \\
   15 \times \frac{V_i - 0.6 T_{\text{mild}}}{0.4 T_{\text{mild}}} & \text{if } 0.6 T_{\text{mild}} \le V_i < T_{\text{mild}} \\
   15 + 20 \times \frac{V_i - T_{\text{mild}}}{T_{\text{mod}} - T_{\text{mild}}} & \text{if } T_{\text{mild}} \le V_i < T_{\text{mod}} \\
   35 + 30 \times \frac{V_i - T_{\text{mod}}}{T_{\text{pron}} - T_{\text{mod}}} & \text{if } T_{\text{mod}} \le V_i < T_{\text{pron}} \\
   65 + 35 \times \min\left(1.0, \frac{V_i - T_{\text{pron}}}{T_{\text{pron}}}\right) & \text{if } V_i \ge T_{\text{pron}}
   \end{cases}$$

2. **Metric Weights ($W_i$):**
   - Head forward angle: $0.40$
   - Trunk inclination: $0.30$
   - Hip line deviation: $0.30$
   - Shoulder tilt: $0.30$
   - Hip tilt: $0.25$
   - Sideways trunk lean: $0.25$
   - Head tilt: $0.20$

### 7.3 Clinical Risk Categorization
- **Low Risk:** Score $\ge 80.0$, and no findings have `moderate` or `pronounced` severity.
- **Medium Risk:** Score between $60.0$ and $79.9$, or contains at least one `moderate` finding.
- **High Risk:** Score $< 60.0$, or contains at least one `pronounced` finding.

---

## 8. Corrective Plan & Clinical Recommendation Engine

### 8.1 Curated Physical Therapy Exercise Library
PostureAI avoids unvetted AI-generated exercises. Corrective routines are drawn from an internal, peer-reviewed clinical library structured into 4 categories:
1. **Mobility (Joint Range-of-Motion):**
   - *Chin tucks:* Restores cervical lordosis and deep cervical flexor endurance.
   - *Seated thoracic extension:* Mobilizes stiff thoracic kyphosis.
2. **Therapeutic Stretches:**
   - *Doorway chest stretch:* Stretches tight pectoralis major and minor muscles.
   - *Upper trapezius & levator scapulae stretch:* Reduces lateral cervical tension.
   - *Kneeling hip flexor stretch:* Relieves tight psoas muscles causing anterior pelvic shift.
3. **Strength & Activation:**
   - *Wall angels:* Activates lower trapezius and serratus anterior.
   - *Side-lying clamshells & glute bridges:* Strengthens the posterior pelvic chain.
4. **Postural Awareness:**
   - *Hourly posture reset:* Realignment cues for desk workers.
   - *Mirror alignment check:* Visual proprioceptive feedback.

### 8.2 Dual-Layer LLM / Rule-Based Explanation Engine
PostureAI uses a **dual-layer architecture** for findings explanations:
- **Layer 1: Local Ollama LLM (`llama3`):**
  - Sends strictly measured numeric facts into a structured JSON prompt.
  - The model provides natural-language summaries of what the angles mean in plain language.
  - The LLM is strictly constrained: it **cannot** alter measurements, scores, or exercises.
- **Layer 2: Deterministic Rule-Based Fallback:**
  - If Ollama is disabled, offline, or times out, the system automatically falls back to deterministic explanations.
  - Generates the exact same validated JSON schema without interruption.

---

## 9. Automated PDF Clinical Report Generation

PostureAI includes an automated PDF generation engine powered by **ReportLab**:

- **Layout Structure:**
  1. **Header Banner:** Medical branding, patient name, evaluation timestamp, and unique UUID reference.
  2. **Anatomical Metrics Table:** Measured angle, reference vertical/horizontal, confidence percentage, and deviation status.
  3. **Visual Alignment Chart:** Vector-drawn biomechanical angle arcs, plumb lines, and side-by-side color-coded severity bars.
  4. **Clinical Findings & Recommendations:** Structured paragraphs detailing observations, therapeutic stretches, strength exercises, and lifestyle adjustments.
  5. **Physician Referral Notice:** Notice advising the patient to share the PDF with a physiotherapist or physician.

---

## 10. Geospatial Provider Discovery (PostGIS & OpenStreetMap)

PostureAI helps patients find physical therapy and spine clinics through an integrated **PostGIS spatial discovery engine**:

```
[Patient Device Geolocation (Lat, Lon)]
                 │
                 ▼
[PostgreSQL + PostGIS Geography Engine]
                 │
   ST_DWithin(location, ST_MakePoint(lon, lat)::geography, radius_meters)
                 │
                 ├───► [Local Database Cache] (Within radius, fetched < 7 days ago)
                 │
                 └───► [OSM Overpass / Nominatim API] (If cache empty, fetches real clinics)
                                 │
                                 ▼
                     [Returns Verified Providers & Distance in KM]
```

- **Spatial Indexing:** Uses `GIST` indices on `geography(POINT, 4326)` for sub-millisecond proximity queries.
- **Deduplication:** Merges nearby healthcare facilities within 50 meters to eliminate duplicate OpenStreetMap nodes.
- **Verified Sources:** Uses real, verified facilities from OpenStreetMap contributors; it does not fabricate contact info or doctor ratings.

---

## 11. Glossary of Terms, Medical Concepts & Technical Definitions

| Term | Domain | Definition |
|---|---|---|
| **Acromion** | Anatomy | The outer end of the scapula spine forming the point of the shoulder; serves as the reference point for shoulder position. |
| **Anterior** | Anatomy | Directed toward or situated at the front surface of the body. |
| **Anterior Pelvic Tilt (APT)** | Biomechanics | A forward tilt of the pelvis where the anterior superior iliac spines move downward and forward, increasing lumbar lordosis. |
| **ASIS** | Anatomy | *Anterior Superior Iliac Spine*: The prominent anterior projection of the ilium; used to assess pelvic symmetry and tilt. |
| **Bilateral** | Clinical | Relating to, affecting, or occurring on both right and left sides of the body. |
| **BlazePose** | Computer Vision | Google's deep neural network architecture designed for real-time single-person 3D body pose estimation from RGB video/images. |
| **Cervical Lordosis** | Biomechanics | The normal inward anterior curvature of the cervical spine (neck). |
| **Coronal / Frontal Plane** | Anatomy | Any vertical plane that divides the body into ventral and dorsal (belly and back) sections. |
| **Craniovertebral Angle (CVA)** | Biomechanics | The angle formed between a horizontal line passing through C7 spinous process and a line connecting C7 to the tragus of the ear. |
| **External Auditory Meatus** | Anatomy | The ear canal opening (ear landmark in MediaPipe); used as the reference point for head position. |
| **Forward Head Posture (FHP)** | Pathology | Anterior positioning of the cervical spine where the head translates forward past the acromion vertical line ("Text Neck"). |
| **Geodesic Distance** | Mathematics | The shortest distance between two points along the curved surface of the earth; calculated using PostGIS spatial algorithms. |
| **GIST Index** | Databases | *Generalized Search Tree*: An indexing mechanism in PostgreSQL used for accelerating spatial and geometric queries. |
| **Kyphosis** | Biomechanics | The normal outward posterior curvature of the thoracic spine; excessive kyphosis is commonly called hunchback. |
| **Laplacian Variance** | Computer Vision | The variance of discrete second-order spatial derivatives across an image; used to detect edge sharpness and focus quality. |
| **Lateral / Sagittal Plane** | Anatomy | An anatomical plane dividing the body into right and left halves; used for side-view posture assessments. |
| **Lordosis** | Biomechanics | The normal inward anterior curvature of the lumbar and cervical regions of the spine. |
| **MediaPipe Tasks** | AI Engineering | Google's cross-platform framework for deploying packaged machine learning vision pipelines. |
| **Oblique View** | Photography | An angular camera perspective (between $30^\circ$ and $55^\circ$ body yaw) that is neither frontal nor lateral. |
| **Pelvic Unleveling** | Pathology | Asymmetry where one iliac crest or ASIS sits higher than the other in the frontal plane. |
| **Plumb Line** | Biomechanics | A vertical gravitational reference line used in posture assessment to evaluate whether body segments align over the base of support. |
| **Posterior** | Anatomy | Directed toward or situated at the back surface of the body. |
| **PostGIS** | Databases | A spatial database extender for PostgreSQL providing spatial data types, functions, and geometric algorithms. |
| **Proprioception** | Physiology | The body's sensory ability to perceive its position, motion, equilibrium, and spatial orientation. |
| **ReportLab** | Software | An open-source Python library for generating dynamic, vector-accurate PDF documents programmatically. |
| **Sagittal Plane** | Anatomy | Longitudinal anatomical plane dividing the body into right and left sections. |
| **Scoliosis** | Pathology | An abnormal lateral curvature of the spine occurring in the coronal plane, often accompanied by vertebral rotation. |
| **SRID 4326** | Geospatial | *Spatial Reference System Identifier 4326*: Standard WGS 84 coordinate reference system used by GPS and OpenStreetMap. |
| **Swayback Posture** | Biomechanics | A posture characterized by anterior pelvic shift, hip hyperextension, increased thoracic kyphosis, and forward head position. |
| **Thoracic Spine** | Anatomy | The middle 12 vertebrae (T1–T12) of the spinal column connecting the cervical and lumbar regions. |
| **Trunk Inclination** | Biomechanics | The angular deviation of the line connecting the shoulder and hip relative to the true vertical plumb line. |
| **Yaw** | Kinematics | Rotation around the vertical axis; in PostureAI, it measures how much the patient's torso is rotated relative to the camera lens. |

---

## 12. Verification & Maintenance Commands

### Build & Run the Full Stack
```bash
# Starts PostGIS, Backend (with MediaPipe & Alembic), and Frontend
docker compose up -d --build
```

### Run Internal Backend Test Suite
```bash
# Runs 100+ isolated unit and integration tests
docker compose exec backend pytest
```

### Inspect Live Container Status
```bash
docker compose ps
docker compose logs backend --tail 50
```

### Healthcheck Endpoint
```bash
curl http://localhost:8001/api/health
# Response: {"status":"ok","pose_model_present":true}
```
