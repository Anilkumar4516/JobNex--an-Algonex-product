#main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection
from analyzer import analyze_resume
import json
from typing import Optional
import apply_db
import auto_apply
from job_fetcher import fetch_jobs, JobFetchError

app = FastAPI()

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
def search_jobs(keyword: str = Query(..., min_length=2), limit: int = 10):
    try:
        return {"jobs": fetch_jobs(keyword, limit)}
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


# Backend API: Retrieve analysis history
@app.get("/api/analyses")
def get_analyses():
    connection = None
    cursor = None

    try:
        # Connect to MySQL
        connection = get_connection()

        # Create a cursor that returns dictionary rows
        cursor = connection.cursor(dictionary=True)

        # Fetch the latest 20 analyses
        query = """SELECT
                Analysis_id,
                matched_score,
                matched_skills,
                missing_skills,
                created_At
            FROM resume_analyzer
            ORDER BY Analysis_id DESC
            LIMIT 20"""

        cursor.execute(query)
        analyses = cursor.fetchall()

        for analysis in analyses:
            for field in ("matched_skills", "missing_skills"):
                value = analysis[field]

                if isinstance(value, str):
                    analysis[field] = json.loads(value)

        return {"analyses": analyses}

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analyses"
        ) from error

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()