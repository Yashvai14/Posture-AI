# 🐳 PostureAI — Complete Docker Startup Guide

This guide is designed for **everyone**—even if you have never used Docker before. Follow these steps sequentially to get PostureAI running on your machine in minutes.

---

## 📑 Table of Contents
1. [What Will Run?](#-what-will-run)
2. [Prerequisites (First-Time Setup)](#-prerequisites-first-time-setup)
3. [Quick Start (One Command)](#-quick-start-one-command)
4. [Accessing the App](#-accessing-the-app)
5. [Useful Commands (Managing the App)](#-useful-commands-managing-the-app)
6. [Optional: Enabling Ollama (Local AI Reasoning)](#-optional-enabling-ollama-local-ai-reasoning)
7. [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 🏗️ What Will Run?

When you start Docker Compose, it builds and boots **three isolated containers** automatically:

| Container Name | Role | Technology | Host Port / URL |
| :--- | :--- | :--- | :--- |
| **`postureai-frontend`** | User Interface | Next.js 14, React, Tailwind CSS | [http://localhost:3000](http://localhost:3000) |
| **`postureai-backend`** | REST API & AI Engine | FastAPI, Python 3.11, MediaPipe | [http://localhost:8001/api](http://localhost:8001/api) |
| **`postureai-db`** | Spatial Database | PostgreSQL 16 + PostGIS 3.4 | `localhost:5433` (internal `5432`) |

> [!NOTE]
> Database migrations (Alembic) run **automatically** inside the backend container upon startup. You do not need to configure PostgreSQL or run SQL scripts manually.

---

## 🧰 Prerequisites (First-Time Setup)

Before running the application, make sure you have **Docker** installed:

### 1. Install Docker Desktop
- **Windows**: Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/). Ensure **WSL 2 backend** is checked during installation.
- **Mac**: Download and install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) (choose Apple Silicon or Intel depending on your Mac).
- **Linux**: Install [Docker Engine](https://docs.docker.com/engine/install/) and the [Docker Compose plugin](https://docs.docker.com/compose/install/linux/).

### 2. Verify Docker is Running
Open a terminal (PowerShell, Command Prompt, or Bash) and run:
```bash
docker --version
docker compose version
```
Both commands should return version numbers.

> [!IMPORTANT]
> Make sure Docker Desktop is open and showing the green **"Engine running"** indicator in the bottom-left corner of the Docker dashboard.

---

## 🚀 Quick Start (One Command)

### Step 1: Open Terminal in the Project Directory
Navigate to the root folder where `docker-compose.yml` is located:
```bash
# Example for Windows:
cd "d:\All Projects\Posture AI"

# Example for Mac / Linux:
cd ~/Posture-AI
```

### Step 2: Build and Start Containers
Run the following command:

```bash
docker compose up --build
```

#### What happens next?
1. Docker will download necessary base images (PostGIS, Python, Node).
2. It will build the backend and frontend images.
3. It will wait for the database health check to pass.
4. It will apply database migrations automatically.
5. It will start both the frontend and backend servers.

> [!TIP]
> **Want to run in the background (detached mode)?**
> Add `-d` to the command:
> ```bash
> docker compose up --build -d
> ```

---

## 🌐 Accessing the App

Once the startup logs stabilize, open your browser:

### 1. Frontend Web App
👉 **[http://localhost:3000](http://localhost:3000)**
- Register a new patient account or log in.
- Upload front and side posture images for AI skeletal assessment.
- Review symptom-based recommendations and discover nearby physiotherapists/clinics.

### 2. Backend Interactive API Documentation (Swagger UI)
👉 **[http://localhost:8001/api/docs](http://localhost:8001/api/docs)**
- Explore and test all REST endpoints directly in your browser.
- Interactive authentication with JWT tokens.

### 3. Backend Health Status
👉 **[http://localhost:8001/api/health](http://localhost:8001/api/health)**
- Expected JSON response:
  ```json
  {
    "status": "ok",
    "pose_model_present": true
  }
  ```

---

## 🛠️ Useful Commands (Managing the App)

### View Live Logs
To monitor logs in real-time across all containers:
```bash
docker compose logs -f
```
To view logs for a specific service:
```bash
# Backend logs only
docker compose logs -f backend

# Frontend logs only
docker compose logs -f frontend

# Database logs only
docker compose logs -f db
```

### Check Container Status
See if all containers are running and healthy:
```bash
docker compose ps
```

### Stop the Application
To stop the running containers safely:
```bash
docker compose stop
```
Or to stop and remove the containers:
```bash
docker compose down
```

### Reset Everything (Fresh Clean Database)
If you want to wipe existing database data and start with an empty slate:
```bash
docker compose down -v
docker compose up --build
```
*(The `-v` flag removes the named Docker volume where PostgreSQL stores tables).*

---

## 🧠 Optional: Enabling Ollama (Local AI Reasoning)

PostureAI works seamlessly out-of-the-box with a deterministic, rule-based expert recommendation engine.

If you wish to enable the local **Ollama LLM** for dynamic clinical reasoning:

1. **Install Ollama** on your host computer from [ollama.com](https://ollama.com/).
2. Pull the default model in your host terminal:
   ```bash
   ollama run llama3
   ```
3. In `docker-compose.yml`, change:
   ```yaml
   OLLAMA_ENABLED: "true"
   ```
4. Restart the backend container:
   ```bash
   docker compose up -d backend
   ```
   *(Docker Compose automatically routes requests to your host's Ollama instance via `http://host.docker.internal:11434`)*.

---

## ❓ Troubleshooting & FAQs

### Q1: Error `Cannot connect to the Docker daemon`
- **Cause**: Docker Desktop is not running.
- **Fix**: Launch the Docker Desktop application from your Start Menu / Applications folder and wait until it indicates it is running.

### Q2: Port Conflict: `port is already allocated`
- **Cause**: Another service on your computer is using port `3000`, `8001`, or `5433`.
- **Fix**: You can override the ports without editing `docker-compose.yml` by setting environment variables in a `.env` file in the root folder:
  ```env
  FRONTEND_PORT=3001
  BACKEND_PORT=8002
  DB_PORT=5434
  ```
  Then run `docker compose up --build`.

### Q3: How do I access the PostgreSQL database directly?
- Connect with any GUI client like **DBeaver**, **pgAdmin**, or **TablePlus**:
  - **Host**: `localhost`
  - **Port**: `5433` (note: mapped to 5433 on your host machine)
  - **Database**: `postureai`
  - **Username**: `postureai`
  - **Password**: `postureai_secure_password_123`

### Q4: MediaPipe Model Missing
The application comes pre-bundled with the pose detection model file located at [backend/models/pose_landmarker_full.task](backend/models/pose_landmarker_full.task). If missing, download it from Google MediaPipe and place it in that folder before building the Docker image.

---

**Need Help?** Check backend logs using `docker compose logs -f backend` or inspect API responses at [http://localhost:8001/api/docs](http://localhost:8001/api/docs).
