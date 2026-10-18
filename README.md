# JobNex -- an Algonex product

JobNex is an intelligent career assistant and automated job application platform built with **FastAPI**, **MySQL**, and **Google Gemini AI**, accompanied by an interactive frontend interface.

---

## 🛠️ Tech Stack
- **Backend:** Python 3.11+, FastAPI, MySQL, Google GenAI (Gemini), Remotive Jobs API, Uvicorn
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Testing:** Python unittest, Starlette TestClient

---

## 🌟 Features
- **Resume & Job Description Analysis:** Match skill sets, identify gaps, compute score percentage, and generate improvement tips.
- **AI-Powered Analysis:** Gemini-powered in-depth resume critique and role suitability assessment.
- **Remote Job Search:** Query live remote tech jobs in real-time via Remotive API with built-in caching.
- **Auto-Apply & Cover Letter Pipeline:** Auto-generate tailored cover letters, queue applications with duplicate detection and match thresholds, and support manual approval workflows.
- **Application Tracking:** Track application states (`queued`, `sent`, `failed`, `manual_required`) with audit logging.

---

## 🚀 Getting Started

### 1. Backend Setup
1. Open a terminal in the `backend/` folder:
   ```bash
   cd backend
   ```
2. Activate your virtual environment:
   ```powershell
   .\Algonex\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Add your MySQL credentials and `GEMINI_API_KEY`.

5. Initialize the database schema (optional if using MySQL Workbench):
   ```bash
   python apply_db.py
   ```

6. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 2. Frontend Setup
Open `Frontend/index.html` in your browser or run with Live Server (port 5500 / 5501).

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check endpoint |
| `POST` | `/api/analyze` | Analyze resume vs job description |
| `GET` | `/api/analyses` | Get recent resume analysis history |
| `GET` | `/api/jobs/search?keyword={query}` | Search live remote jobs |
| `POST` | `/api/applications` | Score & queue job application with auto-generated cover letter |
| `GET` | `/api/applications` | List queued and sent applications |
| `POST` | `/api/applications/{id}/approve` | Approve and dispatch application |
