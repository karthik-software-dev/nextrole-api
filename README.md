# NextRole - Autonomous Job Discovery Engine & Platform

NextRole is an intelligent job discovery, matching, and application tracking platform designed to discover, evaluate, and track high-relevance tech roles across targeted companies.

---

## 🌐 Live Deployments & Repositories

### Live Application
- **Frontend App (Netlify)**: [https://nextrole-app.netlify.app](https://nextrole-app.netlify.app)
- **Backend API Docs (Render)**: [https://nextrole-api-vyzp.onrender.com/docs](https://nextrole-api-vyzp.onrender.com/docs)
- **Backend API Base**: `https://nextrole-api-vyzp.onrender.com/api/v1`

### Standalone GitLab Repositories
- **Frontend UI**: [https://gitlab.com/karthik-software-dev/nextrole-ui](https://gitlab.com/karthik-software-dev/nextrole-ui)
- **Backend API**: [https://gitlab.com/karthik-software-dev/nextrole-api](https://gitlab.com/karthik-software-dev/nextrole-api)

---

## 🌿 Branching Strategy

This repository adheres to a structured Git flow:
- **`main`**: Production-ready, stable releases.
- **`dev`**: Active development branch. All feature branches are merged into `dev`. Once tested, `dev` is merged into `main`.

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.10+
- Node.js 20+
- PostgreSQL database (or local SQLite)

### 2. Backend Setup
```bash
# Setup virtual environment
python -m venv env
.\env\Scripts\Activate.ps1

# Install backend dependencies
pip install -r app/requirements.txt

# Run FastAPI backend
python -m uvicorn --app-dir app server:app --reload --port 8000
```

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install frontend dependencies
npm install

# Run Vite development server
npm run dev
```

---

## 📁 Project Structure

```
job-agent/
├── .gitignore
├── README.md
├── app/                      # FastAPI Backend
│   ├── api/v1/               # REST API endpoints & route handlers
│   ├── config/               # Environment configuration & constants
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # Discovery engines & business logic
│   ├── storage/              # SQLAlchemy database models & sessions
│   ├── requirements.txt      # Python dependencies
│   └── server.py             # FastAPI entrypoint
└── frontend/                 # React 19 + Vite Frontend
    ├── src/
    │   ├── api/              # Axios API clients & interceptors
    │   ├── components/       # UI & Dashboard components
    │   ├── pages/            # Page views (Dashboard, Jobs, Analytics)
    │   └── context/          # State management providers
    └── package.json
```
