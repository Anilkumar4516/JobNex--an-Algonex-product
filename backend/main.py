#main.py
from contextlib import asynccontextmanager
from datetime import date as date_type
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from database import get_connection
from analyzer import analyze_resume
import json
from typing import Optional
import apply_db
import auto_apply
import daily_db
import daily_jobs
import daily_scheduler
from job_fetcher import fetch_jobs, JobFetchError, job_source, normalize_region


@asynccontextmanager
async def lifespan(app):
    try:
        apply_db.create_table()
        daily_db.create_tables()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_analyzer (
                Analysis_id INT AUTO_INCREMENT PRIMARY KEY,
                resume_text LONGTEXT NOT NULL,
                jd_text LONGTEXT NOT NULL,
                matched_skills JSON NULL,
                missing_skills JSON NULL,
                matched_score DECIMAL(5,2) NOT NULL DEFAULT 0,
                suggestions JSON NULL,
                created_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[Lifespan] DB init note: {e}")

    # Start the daily trigger when the API starts, stop it when the API stops.
    daily_scheduler.start()
    yield
    daily_scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    resume_text: str
    jd_text: str


@app.get("/")
def home():
    return {
        "message": "Resume Analyzer Backend is Running"
    }


@app.post("/api/analyze")
@app.post("/api/analyse")
def analyze(request: AnalyzeRequest):
    result = analyze_resume(request.resume_text,request.jd_text)
    print(result)
    connection = None
    cursor = None
    analysis_id = None

    try:
        connection = get_connection()
        cursor = connection.cursor()
        query = """
            INSERT INTO resume_analyzer (resume_text, jd_text, matched_skills, missing_skills, matched_score, suggestions)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query, (
                request.resume_text,
                request.jd_text,
                json.dumps(result["matched_skills"]),
                json.dumps(result["missing_skills"]),
                result["matched_score"],
                json.dumps(result["suggestions"])
            )
        )

        connection.commit()
        analysis_id = cursor.lastrowid

        
        
    except Exception as error:
        if connection is not None and connection.is_connected():
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to save analysis"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
    return {
        "Analysis_Id": analysis_id,
        **result
    }


# ---------------- Auto-apply feature ----------------

class queueApplicationRequest(BaseModel):
    resume_text: str
    job_title: str
    company: str
    job_description: str
    job_url: Optional[str] = None
    apply_email: Optional[str] = None


# Step 1: find real jobs for a keyword
@app.get("/api/jobs/search")
def search_jobs(keyword: str = Query(..., min_length=2), limit: int = 10,
                region: str = "global"):
    try:
        return {
            "region": region.strip().lower(),
            "source": job_source(region),
            "jobs": fetch_jobs(keyword, limit, region),
        }
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except JobFetchError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

# Step 2: score the job, write a cover letter and queue it for approval
@app.post("/api/applications")
def queue_application(request: queueApplicationRequest):
    try:
        return auto_apply.queue_application(
            request.resume_text,
            request.job_title,
            request.company,
            request.job_description,
            request.job_url,
            request.apply_email,
        )
    except auto_apply.DuplicateApplicationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (auto_apply.InvalidApplicationError, auto_apply.LowMatchError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to queue application"
        ) from error


# Step 3: list every queued / sent application
@app.get("/api/applications")
def get_applications():
    try:
        return {"applications": apply_db.list_applications()}
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve applications"
        ) from error


# Step 4: the user approves one application and it is sent
@app.post("/api/applications/{application_id}/approve")
def approve_application(application_id: int):
    try:
        return auto_apply.apply_to_application(application_id)
    except auto_apply.ApplicationNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except auto_apply.DailyLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to send application"
        ) from error

# ---------------- Daily matches feature ----------------

class DailySettingsRequest(BaseModel):
    resume_text: str = Field(..., min_length=20)
    keywords: str = Field(..., min_length=2)
    min_score: float = Field(60, ge=0, le=100)
    run_hour: int = Field(9, ge=0, le=23)
    run_minute: int = Field(0, ge=0, le=59)
    enabled: bool = True


def _settings_response():
    settings = daily_db.get_settings()
    last_run = settings["last_run_date"]
    settings["last_run_date"] = last_run.isoformat() if last_run else None
    settings["next_run"] = daily_scheduler.next_run_time()
    return settings


# Read the saved resume / keywords / threshold / run time
@app.get("/api/daily/settings")
def get_daily_settings():
    try:
        daily_db.create_tables()
        return _settings_response()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to load daily settings"
        ) from error


# Save them and move the daily trigger to the new time
@app.put("/api/daily/settings")
def save_daily_settings(request: DailySettingsRequest):
    if not daily_jobs.split_keywords(request.keywords):
        raise HTTPException(status_code=422, detail="Add at least one keyword")

    try:
        daily_db.create_tables()
        daily_db.save_settings(
            request.resume_text.strip(),
            request.keywords.strip(),
            request.min_score,
            request.run_hour,
            request.run_minute,
            request.enabled,
        )
        daily_scheduler.apply_schedule(
            request.enabled, request.run_hour, request.run_minute
        )
        return _settings_response()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to save daily settings"
        ) from error


# Run the daily job right now (same code the trigger runs every day)
@app.post("/api/daily/run")
def run_daily_now():
    try:
        return daily_jobs.run_daily()
    except daily_jobs.RunAlreadyActiveError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except daily_jobs.DailyRunError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Daily run failed"
        ) from error


# The UI list: ONE day (default today), only jobs at or above the match percent
@app.get("/api/daily/jobs")
def get_daily_jobs(
    min_score: Optional[float] = Query(None, ge=0, le=100),
    day: Optional[date_type] = None,
):
    try:
        run_date = day or daily_jobs.today()

        if min_score is None:
            min_score = daily_db.get_settings()["min_score"]

        jobs = daily_db.list_matches(run_date, min_score)
        total = daily_db.count_matches(run_date)

        return {
            "date": run_date.isoformat(),
            "min_score": min_score,
            "count": len(jobs),
            "hidden_below_min": total - len(jobs),
            "jobs": jobs,
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve daily jobs"
        ) from error
# Backend API: Retrieve analysis history for Workbench
@app.get("/api/analyses")
def get_analyses():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        query = """SELECT
                Analysis_id,
                matched_score,
                matched_skills,
                missing_skills,
                suggestions,
                SUBSTRING(resume_text, 1, 100) AS resume_preview,
                SUBSTRING(jd_text, 1, 100) AS jd_preview,
                created_At
            FROM resume_analyzer
            ORDER BY Analysis_id DESC
            LIMIT 50"""

        cursor.execute(query)
        analyses = cursor.fetchall()

        for analysis in analyses:
            for field in ("matched_skills", "missing_skills", "suggestions"):
                value = analysis.get(field)
                if isinstance(value, str):
                    try:
                        analysis[field] = json.loads(value)
                    except Exception:
                        pass
            if hasattr(analysis.get("created_At"), "isoformat"):
                analysis["created_At"] = analysis["created_At"].isoformat()

        return {"analyses": analyses}

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analyses: {error}"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.get("/api/analyses/{analysis_id}")
def get_analysis_detail(analysis_id: int):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM resume_analyzer WHERE Analysis_id = %s",
            (analysis_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")

        for field in ("matched_skills", "missing_skills", "suggestions"):
            val = row.get(field)
            if isinstance(val, str):
                try:
                    row[field] = json.loads(val)
                except Exception:
                    pass
        if hasattr(row.get("created_At"), "isoformat"):
            row["created_At"] = row["created_At"].isoformat()

        return row
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.delete("/api/analyses/{analysis_id}")
def delete_analysis(analysis_id: int):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM resume_analyzer WHERE Analysis_id = %s", (analysis_id,))
        connection.commit()
        return {"status": "deleted", "analysis_id": analysis_id}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# ---------------- Chatbot Endpoint ----------------

class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = None


@app.post("/api/chat")
def chat_with_jobnex(req: ChatRequest):
    import ai_analyzer
    return ai_analyzer.chat_with_assistant(req.message, req.history)


# ---------------- Interview Prep Endpoint ----------------

class InterviewPrepRequest(BaseModel):
    job_title: str
    job_description: Optional[str] = ""
    resume_text: Optional[str] = ""


@app.post("/api/interview/prep")
def interview_prep_endpoint(req: InterviewPrepRequest):
    import interview_prep
    return interview_prep.generate_interview_prep(
        job_title=req.job_title,
        job_description=req.job_description,
        resume_text=req.resume_text,
    )


# ---------------- Email Referral & HR Outreach Endpoints ----------------

class ReferralEmailRequest(BaseModel):
    applicant_name: Optional[str] = None
    job_title: str
    job_id_or_url: str
    target_company: Optional[str] = "Google"
    referrer_name: Optional[str] = "Team Member"
    top_skills: Optional[list] = None
    portfolio_or_linkedin: Optional[str] = ""
    access_type: Optional[str] = "public"


@app.post("/api/referrals/generate")
def generate_referral_endpoint(req: ReferralEmailRequest):
    import automatic_job_email_referrals
    return automatic_job_email_referrals.generate_google_referral_email(
        applicant_name=req.applicant_name,
        job_title=req.job_title,
        job_id_or_url=req.job_id_or_url,
        target_company=req.target_company,
        referrer_name=req.referrer_name,
        top_skills=req.top_skills,
        portfolio_or_linkedin=req.portfolio_or_linkedin,
        access_type=req.access_type,
    )


class DirectRecruiterEmailRequest(BaseModel):
    applicant_name: Optional[str] = None
    job_title: str
    company: str
    hr_email: Optional[str] = None
    recruiter_name: Optional[str] = None
    matched_skills: Optional[list] = None
    resume_summary: Optional[str] = ""


@app.post("/api/referrals/generate-recruiter")
def generate_recruiter_endpoint(req: DirectRecruiterEmailRequest):
    import automatic_job_email_referrals
    return automatic_job_email_referrals.generate_direct_recruiter_email(
        applicant_name=req.applicant_name,
        job_title=req.job_title,
        company=req.company,
        hr_email=req.hr_email,
        recruiter_name=req.recruiter_name,
        matched_skills=req.matched_skills,
        resume_summary=req.resume_summary,
    )


class HRScrapeRequest(BaseModel):
    url: str


@app.post("/api/hr/scrape")
def scrape_hr_endpoint(req: HRScrapeRequest):
    import automatic_job_email_referrals
    return automatic_job_email_referrals.scrape_hr_contacts_from_url(req.url)


class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str


@app.post("/api/referrals/send")
def send_referral_endpoint(req: SendEmailRequest):
    import automatic_job_email_referrals
    try:
        return automatic_job_email_referrals.send_referral_email_direct(
            to_email=req.to_email,
            subject=req.subject,
            body=req.body,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------- Batch Auto-Apply Endpoint ----------------

class AutoBatchRequest(BaseModel):
    keyword: str
    resume_text: Optional[str] = None
    limit: Optional[int] = 5
    region: Optional[str] = "global"


@app.post("/api/applications/auto-batch")
def auto_batch_apply_endpoint(req: AutoBatchRequest):
    try:
        return auto_apply.auto_scrape_and_apply_batch(
            keyword=req.keyword,
            resume_text=req.resume_text,
            limit=req.limit,
            region=req.region,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ---------------- GenAI Job Data Scraping Endpoints ----------------

class JobScrapeRequest(BaseModel):
    url: str


@app.post("/api/jobs/scrape")
def scrape_job_endpoint(req: JobScrapeRequest):
    """
    Automatically scrape and extract structured job data from any job URL
    using Google GenAI (Gemini) with intelligent fallback.
    """
    try:
        details = auto_apply.scrape_job_from_url(req.url)
        return details
    except auto_apply.ApplyError as err:
        raise HTTPException(status_code=422, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to scrape job data: {err}")


class AutoScrapeApplyRequest(BaseModel):
    job_url: str
    resume_text: Optional[str] = None
    apply_email: Optional[str] = None


@app.post("/api/applications/auto-scrape-apply")
def auto_scrape_apply_endpoint(req: AutoScrapeApplyRequest):
    """
    Automatically scrape online job details from a URL using GenAI,
    score against the candidate's resume, generate a cover letter, and queue application.
    """
    try:
        return auto_apply.auto_scrape_and_apply(
            job_url=req.job_url,
            resume_text=req.resume_text,
            apply_email=req.apply_email,
        )
    except auto_apply.DuplicateApplicationError as err:
        raise HTTPException(status_code=409, detail=str(err))
    except (auto_apply.InvalidApplicationError, auto_apply.LowMatchError) as err:
        raise HTTPException(status_code=422, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Auto-scrape apply failed: {err}")
