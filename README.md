# Job Agent - Autonomous Job Discovery Engine

An automated job discovery and relevance filtering agent designed to find, evaluate, and score relevant tech roles (e.g., Python Backend Engineering) across job platforms.

---

## 🌿 Branching Strategy

This repository adheres to a structured Git flow:
- **`main`**: Production-ready, stable releases.
- **`dev`**: Active development branch. All feature branches are merged into `dev`. Once tested, `dev` is merged into `main`.

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.10+
- Apify Account & API Token

### 2. Setup Virtual Environment
```bash
# From job-agent directory
python -m venv env
# On Windows PowerShell:
.\env\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r app/requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env` inside `app/`:
```bash
cp app/.env.example app/.env
```
Add your Apify API token in `app/.env`:
```env
APIFY_API_TOKEN=your_apify_api_token_here
```

### 5. Run the Agent
```bash
cd app
python main.py
```

---

## 📁 Project Structure

```
job-agent/
├── .gitignore
├── README.md
├── app/
│   ├── .env.example
│   ├── config.py             # Environment configuration & token validation
│   ├── main.py               # Orchestrator CLI entrypoint
│   ├── requirements.txt      # Project dependencies
│   ├── processing/
│   │   └── relevance.py      # Heuristic scoring & filtering engine
│   └── sources/
│       └── indeed_source.py  # Apify Indeed scraper integration
```
