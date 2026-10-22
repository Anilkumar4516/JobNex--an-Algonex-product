# JobNex -- an Algonex product

**JobNex** is an intelligent AI career assistant and automated job application platform built with **FastAPI**, **MySQL**, and **Google Gemini AI**, accompanied by a multi-tab web interface.

---

## 🛠️ Technology Stack
- **Backend:** Python 3.11+, FastAPI, MySQL Connector, Google GenAI SDK (Gemini 2.5 Flash, 2.0 Flash, 1.5 Flash), BeautifulSoup4, Remotive Jobs API, APScheduler, Uvicorn
- **Frontend:** HTML5, CSS3 (Modern Glassmorphism Dark Theme), JavaScript (Vanilla)
- **Documentation:** Interactive OpenAPI / Swagger UI (`/docs`), ReDoc (`/redoc`)
- **Testing:** Python unittest, Starlette TestClient (58 automated unit tests)

---

## 🌟 Key Features

### 1. 🤖 GenAI Job Description Scraper
- Provide any careers/job posting URL (e.g. `https://company.com/careers/job-posting`).
- Automatically fetches and cleans webpage HTML, extracting structured fields via Google GenAI:
  - `job_title`, `company`, `job_description`, `apply_email`, `location`, `job_type`, and `required_skills`.
  - Built-in curated fallbacks for offline testing (`Northwind Labs`, `Brightpath Systems`).

### 2. 📄 Resume & Job Description Analysis (ATS Score)
- Compares resume text against job requirements to compute match percentages (0–100%).
- Identifies matching skills and missing qualifications with targeted suggestions.
- Automatically saves analysis history to MySQL Workbench (`resume_analyzer` table).

### 3. 🎯 Interview Preparation with Detailed Answer Tips
- Generates role-specific behavioral and technical interview questions for any company.
- Every question includes comprehensive **Answer Tips**:
  - **Key Points** to highlight.
  - **STAR Framework** breakdown (Situation, Task, Action, Result).
  - **Sample Answer Points** demonstrating industry best practices.
  - **Pitfalls to Avoid** during the interview.

### 4. ✉️ Automated Job Referral & HR Email Scraper
- Automatically scrapes recruiter/HR contact emails from online career links.
- Generates tailored referral outreach emails for FAANG (Google, Microsoft) and high-growth startups.
- Supports switching between public employee outreach and private direct recruiter access.

### 5. ⚡ Auto-Apply & Tailored Cover Letter Pipeline
- Automatically writes personalized cover letters emphasizing candidate skills.
- Queues applications with duplicate detection and minimum match thresholds.
- Safe human-in-the-loop approval workflow: send applications via SMTP with resume PDF attached.

### 6. 🕒 Automated Daily Job Matching & Scheduler
- Background scheduler triggers daily keyword scans across live remote tech jobs.
- Automatically matches active listings against candidate resumes and stores recommendations for review.

### 7. 💬 AI Career Assistant Chatbot
- Interactive career advisor answering resume, interview, and job search questions.
- Powered by Google Gemini AI with intelligent rule-based local fallback when offline.

### 8. 🗄️ MySQL Workbench Live Viewer
- Built-in frontend tab to view, refresh, inspect, and delete saved resume analysis records in real time.

---

## 🚀 Getting Started

### 1. Backend Setup
1. Open a terminal in the project directory:
   ```powershell
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
   copy .env.example .env
   ```
   Add your MySQL credentials and optional `GEMINI_API_KEY`. (If `GEMINI_API_KEY` is not provided, JobNex automatically uses its built-in smart AI fallback engine).

5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 2. Interactive API Documentation (Swagger UI)
Once the server is running, open:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3. Frontend Setup
Open `Frontend/index.html` directly in your browser or run via Live Server.

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API health check |
| `POST` | `/api/analyze` | Analyze resume vs job description and save to database |
| `GET` | `/api/analyses` | Get saved resume analysis history |
| `DELETE` | `/api/analyses/{id}` | Delete a saved analysis record |
| `POST` | `/api/chat` | AI Career Assistant Chatbot |
| `POST` | `/api/jobs/scrape` | GenAI online job description scraper |
| `POST` | `/api/interview/prep` | Interview questions with detailed Answer Tips |
| `POST` | `/api/referrals/generate` | Generate tailored referral outreach email |
| `POST` | `/api/hr/scrape` | Scrape HR/recruiter emails from career URLs |
| `GET` | `/api/jobs/search` | Search live remote jobs with region and keyword filters |
| `POST` | `/api/applications` | Score and queue job application |
| `GET` | `/api/applications` | List pending and sent applications |
| `POST` | `/api/applications/{id}/approve` | Approve and send application email via SMTP |
| `POST` | `/api/applications/auto-scrape-apply` | One-click scrape URL, score with AI, and queue |
| `GET` | `/api/daily/settings` | Get daily scheduler settings |
| `PUT` | `/api/daily/settings` | Update daily scheduler configuration |
| `POST` | `/api/daily/run` | Execute immediate daily job match run |
| `GET` | `/api/daily/jobs` | Retrieve daily matched jobs |

---

## 🧪 Running Automated Tests

Run the full automated test suite (58 unit tests):
```powershell
python -m unittest discover backend -v
```

All 58 tests verify:
- API endpoint behaviors and request validation
- GenAI scraper and fallback URL parsing
- Interview prep with STAR framework & answer tips
- Search filters and region normalization
- Daily scheduler matching and database persistence
- SMTP email dispatch and duplicate prevention
