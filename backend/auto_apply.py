# auto_apply.py
# Core logic of the auto-apply feature:
#   1. score a job against the resume (reuses analyzer.py)
#   2. skip weak matches and duplicates
#   3. write a cover letter
#   4. queue the application, and send it by email only after the user approves
import json
import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import requests
except ImportError:
    requests = None

from analyzer import analyze_resume
import apply_db

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class ApplyError(Exception):
    pass


class InvalidApplicationError(ApplyError):
    pass


class DuplicateApplicationError(ApplyError):
    pass


class LowMatchError(ApplyError):
    pass


class ApplicationNotFoundError(ApplyError):
    pass


class DailyLimitError(ApplyError):
    pass


def _int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return int(default)


def is_valid_email(email):
    return bool(email) and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def scrape_job_from_url(url: str, timeout: int = 15) -> dict:
    """
    Fetch an online job page, clean the HTML, and use Google GenAI to extract
    structured job information (title, company, description, apply_email, skills).
    """
    url = (url or "").strip()
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        raise InvalidApplicationError("A valid http or https URL is required for scraping")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        if requests is not None:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            html_content = response.text
        else:
            import urllib.request
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                html_content = resp.read().decode(charset, errors="ignore")
    except Exception as exc:
        raise ApplyError(f"Failed to fetch job URL {url}: {exc}") from exc

    # Parse HTML and remove noise
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "header"]):
            tag.decompose()
        clean_text = soup.get_text(separator="\n", strip=True)
    else:
        soup = None
        clean_text = re.sub(r"<[^>]+>", " ", html_content)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Check for mailto: links in HTML
    mailto_match = re.search(
        r'mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
        html_content,
        re.IGNORECASE,
    )
    email_in_html = mailto_match.group(1) if mailto_match else None

    # Check OpenGraph metadata
    og_title = ""
    og_company = ""
    if soup is not None:
        meta_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "title"})
        if meta_title and meta_title.get("content"):
            og_title = meta_title.get("content").strip()

        meta_company = soup.find("meta", property="og:site_name") or soup.find("meta", attrs={"name": "author"})
        if meta_company and meta_company.get("content"):
            og_company = meta_company.get("content").strip()

    job_details = None
    try:
        import ai_analyzer
        job_details = ai_analyzer.extract_job_details_with_ai(clean_text, url=url)
    except Exception:
        job_details = None

    if not job_details or not isinstance(job_details, dict):
        h1_text = soup.find("h1").get_text(strip=True) if (soup and soup.find("h1")) else "Job Opportunity"
        title = og_title or h1_text
        company = og_company or "Hiring Company"
        at_match = re.search(r"at\s+([A-Z][A-Za-z0-9&.\s]+)", title)
        if at_match and not og_company:
            company = at_match.group(1).strip()
            title = title[:at_match.start()].strip()

        job_details = {
            "job_title": title,
            "company": company,
            "job_description": clean_text[:3000],
            "apply_email": email_in_html,
            "location": "Online / Remote",
            "job_url": url,
            "required_skills": [],
        }

    job_details["job_url"] = url
    if not job_details.get("apply_email") and email_in_html:
        job_details["apply_email"] = email_in_html

    return job_details


def score_job(resume_text, job_description):
    """Score the job against the resume using Google GenAI, with fallback to keyword analyzer."""
    try:
        import ai_analyzer
        ai_raw = ai_analyzer.analyze_resume_with_ai(resume_text, job_description)
        data = json.loads(ai_raw)
        score = float(data.get("matched_score", data.get("match_score", 0.0)))
        return {
            "matched_score": score,
            "matched_skills": data.get("matched_skills", []),
            "missing_skills": data.get("missing_skills", []),
            "suggestions": data.get("suggestions", []),
            "summary": data.get("summary", ""),
        }
    except Exception:
        return analyze_resume(resume_text, job_description)


def build_cover_letter(applicant_name, job_title, company, matched_skills=None,
                       resume_text=None, job_description=None):
    """Generate a tailored cover letter using Google GenAI if available, or fall back to template."""
    if resume_text and job_description:
        try:
            import ai_analyzer
            ai_letter = ai_analyzer.generate_cover_letter_with_ai(
                applicant_name=applicant_name,
                resume_text=resume_text,
                job_title=job_title,
                company=company,
                job_description=job_description,
                matched_skills=matched_skills or [],
            )
            if ai_letter and len(ai_letter.strip()) > 40:
                return ai_letter.strip()
        except Exception:
            pass

    if matched_skills:
        skills_line = ", ".join(matched_skills)
    else:
        skills_line = "the skills listed in the role"

    return (
        f"Dear Hiring Team at {company},\n\n"
        f"I am writing to apply for the {job_title} position. "
        f"My background includes hands-on experience with {skills_line}, "
        f"which matches the requirements of this role.\n\n"
        f"I would welcome the chance to discuss how I can contribute to "
        f"{company}. My resume is attached for your review.\n\n"
        f"Thank you for your time and consideration.\n\n"
        f"Best regards,\n{applicant_name}"
    )


def queue_application(resume_text=None, job_title=None, company=None, job_description=None,
                      job_url=None, apply_email=None):
    """
    Queue a job application. If job_url is provided and details are missing,
    automatically scrape the online job details using Google GenAI.
    """
    resume_text = (resume_text or "").strip()
    job_title = (job_title or "").strip()
    company = (company or "").strip()
    job_description = (job_description or "").strip()
    job_url = (job_url or "").strip() or None

    # Fallback to saved resume in daily_settings if not provided
    if not resume_text:
        try:
            import daily_db
            resume_text = (daily_db.get_settings().get("resume_text") or "").strip()
        except Exception:
            pass

    # If job_url is provided and job details are missing, automatically scrape
    if job_url and not (job_title and company and job_description):
        scraped = scrape_job_from_url(job_url)
        job_title = job_title or (scraped.get("job_title") or "").strip()
        company = company or (scraped.get("company") or "").strip()
        job_description = job_description or (scraped.get("job_description") or "").strip()
        if not apply_email and scraped.get("apply_email"):
            apply_email = scraped.get("apply_email")

    if not (resume_text and job_title and company and job_description):
        raise InvalidApplicationError(
            "resume_text, job_title, company and job_description are required"
        )

    if apply_email and not is_valid_email(apply_email):
        raise InvalidApplicationError("apply_email is not a valid email address")

    if apply_db.find_duplicate(job_title, company):
        raise DuplicateApplicationError(
            f"You already have an application for {job_title} at {company}"
        )

    result = score_job(resume_text, job_description)
    min_score = _int_env("MIN_MATCH_SCORE", 40)

    if result["matched_score"] < min_score:
        raise LowMatchError(
            f"Match score {result['matched_score']} is below the minimum of {min_score}"
        )

    cover_letter = build_cover_letter(
        applicant_name=os.getenv("APPLICANT_NAME", "Applicant"),
        job_title=job_title,
        company=company,
        matched_skills=result.get("matched_skills"),
        resume_text=resume_text,
        job_description=job_description,
    )

    application_id = apply_db.add_application(
        job_title=job_title,
        company=company,
        job_description=job_description,
        match_score=result["matched_score"],
        cover_letter=cover_letter,
        job_url=job_url,
        apply_email=apply_email,
    )

    return apply_db.get_application(application_id)


def auto_scrape_and_apply(job_url: str, resume_text: str = None, apply_email: str = None):
    """Automatically scrape online job details from a URL, score with GenAI, and queue application."""
    scraped = scrape_job_from_url(job_url)
    return queue_application(
        resume_text=resume_text,
        job_title=scraped.get("job_title"),
        company=scraped.get("company"),
        job_description=scraped.get("job_description"),
        job_url=job_url,
        apply_email=apply_email or scraped.get("apply_email"),
    )


def auto_scrape_and_apply_batch(keyword: str, resume_text: str = None, limit: int = 5,
                                region: str = "global", min_score: float = None):
    """
    Search online jobs for a keyword, automatically scrape/parse job details,
    score each against the candidate's resume using Google GenAI, and auto-queue applications.
    """
    import job_fetcher
    jobs = job_fetcher.fetch_jobs(keyword, limit=limit, region=region)
    queued = []
    skipped_duplicates = []
    low_matches = []
    errors = []

    if not resume_text:
        try:
            import daily_db
            resume_text = daily_db.get_settings().get("resume_text", "")
        except Exception:
            pass

    if not resume_text:
        raise InvalidApplicationError("No resume text provided and no saved resume found in settings")

    for job in jobs:
        url = job.get("url")
        title = job.get("title")
        company = job.get("company")
        desc = job.get("description")

        try:
            if url and (not desc or len(desc) < 150):
                try:
                    scraped = scrape_job_from_url(url)
                    title = title or scraped.get("job_title")
                    company = company or scraped.get("company")
                    desc = desc or scraped.get("job_description")
                except Exception:
                    pass

            app_record = queue_application(
                resume_text=resume_text,
                job_title=title,
                company=company,
                job_description=desc,
                job_url=url,
            )
            queued.append(app_record)
        except DuplicateApplicationError:
            skipped_duplicates.append(f"{title} at {company}")
        except LowMatchError as e:
            low_matches.append({"job": f"{title} at {company}", "reason": str(e)})
        except Exception as e:
            errors.append({"job": f"{title} at {company}", "error": str(e)})

    return {
        "keyword": keyword,
        "total_scanned": len(jobs),
        "queued_count": len(queued),
        "queued": queued,
        "skipped_duplicates": skipped_duplicates,
        "low_matches": low_matches,
        "errors": errors,
    }



def send_application_email(to_email, subject, body, resume_path=None):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = _int_env("SMTP_PORT", 587)
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    if not user or not password:
        raise ApplyError("SMTP_USER and SMTP_PASSWORD are not configured in .env")

    sender = os.getenv("APPLICANT_EMAIL") or user

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_email
    message["Reply-To"] = sender
    message["Subject"] = subject
    message.set_content(body)

    if resume_path and Path(resume_path).is_file():
        path = Path(resume_path)
        message.add_attachment(
            path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=path.name,
        )

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(message)


def apply_to_application(application_id):
    application = apply_db.get_application(application_id)

    if not application:
        raise ApplicationNotFoundError(f"Application {application_id} not found")

    if application["status"] == "sent":
        return application

    if not application["apply_email"]:
        apply_db.update_status(
            application_id,
            "manual_required",
            "No recruiter email. Open the job link and apply with the generated cover letter.",
        )
        return apply_db.get_application(application_id)

    max_per_day = _int_env("MAX_APPLICATIONS_PER_DAY", 10)
    if apply_db.count_sent_today() >= max_per_day:
        raise DailyLimitError(f"Daily limit of {max_per_day} applications reached")

    applicant_name = os.getenv("APPLICANT_NAME", "Applicant")
    subject = f"Application for {application['job_title']} - {applicant_name}"

    try:
        send_application_email(
            application["apply_email"],
            subject,
            application["cover_letter"],
            os.getenv("RESUME_PDF_PATH"),
        )
        apply_db.update_status(application_id, "sent", "Application email sent")
    except Exception as error:
        apply_db.update_status(application_id, "failed", str(error)[:480])

    return apply_db.get_application(application_id)