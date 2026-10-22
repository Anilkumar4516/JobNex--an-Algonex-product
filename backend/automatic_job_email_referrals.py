# automatic_job_email_referrals.py
# Specialized module for JobNex automated job referral emails and HR outreach.
# Supports:
#   1. Automatic HR / recruiter email scraping from job postings and company URLs
#   2. High-converting referral request emails for top tech companies (Google, Meta, startups)
#   3. Direct employee referral email generation with public vs private access info
#   4. Direct SMTP email delivery or queueing for user review
import json
import os
import re
import urllib.parse
from pathlib import Path
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import requests
except ImportError:
    requests = None

import auto_apply
import apply_db

# Recruiter and HR email address regex patterns
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
HR_KEYWORDS = ("hr", "career", "talent", "recruit", "jobs", "hiring", "people", "apply")


def scrape_hr_contacts_from_url(url: str, timeout: int = 15) -> dict:
    """
    Scrape a job posting or company careers URL to automatically find
    HR, talent acquisition, or recruiter email addresses and names.
    """
    url = (url or "").strip()
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return {
            "hr_email": None,
            "all_emails": [],
            "recruiter_hint": None,
            "status": "invalid_url"
        }

    html_content = ""
    try:
        if requests is not None:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            html_content = resp.text
        else:
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "JobNex/1.0 (Job Assistant)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                html_content = resp.read().decode(charset, errors="ignore")
    except Exception as exc:
        return {
            "hr_email": None,
            "all_emails": [],
            "recruiter_hint": None,
            "status": f"scrape_failed: {str(exc)}"
        }

    mailto_emails = set()
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)

        # 1. Search for mailto links first
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                clean_email = href.split("?")[0].replace("mailto:", "").strip()
                if auto_apply.is_valid_email(clean_email):
                    mailto_emails.add(clean_email.lower())
    else:
        text = html_content

    # 2. Search all email matches in page text
    text_emails = set(EMAIL_REGEX.findall(text))
    valid_emails = set()
    for e in mailto_emails.union(text_emails):
        # Exclude common image/font extensions or asset dummy emails
        if not re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js)$", e, re.I):
            valid_emails.add(e.lower())

    # 3. Prioritize HR/recruiting emails
    hr_priority = []
    other_emails = []
    for email in sorted(valid_emails):
        user_part = email.split("@")[0].lower()
        if any(kw in user_part for kw in HR_KEYWORDS):
            hr_priority.append(email)
        else:
            other_emails.append(email)

    best_hr_email = hr_priority[0] if hr_priority else (other_emails[0] if other_emails else None)

    # Check for recruiter or contact name in HTML
    recruiter_name = None
    name_match = re.search(r"(?:recruiter|hiring manager|contact|posted by)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)", text, re.I)
    if name_match:
        recruiter_name = name_match.group(1).strip()

    return {
        "hr_email": best_hr_email,
        "all_emails": list(valid_emails),
        "recruiter_hint": recruiter_name,
        "status": "found" if best_hr_email else "no_emails_found"
    }


def generate_google_referral_email(
    applicant_name: str,
    job_title: str,
    job_id_or_url: str,
    target_company: str = "Google",
    referrer_name: str = "Team Member",
    top_skills: list = None,
    portfolio_or_linkedin: str = "",
    access_type: str = "public",  # "public" or "private"
) -> dict:
    """
    Generate a high-converting referral request email targeted for Google or top tech companies.
    Distinguishes between public job board links and private employee internal access.
    """
    applicant = applicant_name or os.getenv("APPLICANT_NAME", "Job Applicant")
    skills_text = ", ".join(top_skills) if top_skills else "Python, Cloud Architecture, and Software Engineering"

    access_note = (
        f"Job Portal Link (Public Access): {job_id_or_url}"
        if access_type == "public"
        else f"Internal Job Requisition ID (Private Employee Access): {job_id_or_url}"
    )

    subject = f"Employee Referral Request: {job_title} at {target_company} - {applicant}"

    body = f"""Hi {referrer_name},

I hope this message finds you well!

I noticed your incredible journey at {target_company} and wanted to reach out. I am currently applying for the {job_title} role at {target_company} and believe my experience directly aligns with what the team is building.

Key Highlights of my qualifications:
• Core Expertise: {skills_text}
• Track Record: Delivered high-impact backend systems, APIs, and automated tools with proven performance and reliability.
• Passion for {target_company}: Excited about the team's engineering standards and product vision.

{access_note}
{f"LinkedIn / Portfolio: {portfolio_or_linkedin}" if portfolio_or_linkedin else ""}

Would you be open to submitting an internal referral for me for this position? I have attached my resume for your quick review and would be grateful for 5 minutes of your time.

Thank you so much for your support and guidance!

Warm regards,
{applicant}
"""
    return {
        "subject": subject,
        "body": body.strip(),
        "target_company": target_company,
        "access_type": access_type,
        "recipient": referrer_name,
    }


def generate_direct_recruiter_email(
    applicant_name: str,
    job_title: str,
    company: str,
    hr_email: str = None,
    recruiter_name: str = None,
    matched_skills: list = None,
    resume_summary: str = "",
) -> dict:
    """
    Generate a concise, professional direct outreach email to a company HR or recruiter.
    """
    applicant = applicant_name or os.getenv("APPLICANT_NAME", "Job Applicant")
    recruiter = recruiter_name or "Hiring Team"
    skills_str = ", ".join(matched_skills) if matched_skills else "Python, FastAPI, MySQL, and full-stack engineering"

    subject = f"Application / Inquiry: {job_title} - {applicant}"

    body = f"""Dear {recruiter},

I am writing to express my strong enthusiasm for the {job_title} opportunity at {company}.

With deep hands-on experience in {skills_str}, I have designed, tested, and scaled software solutions that solve real business problems. {resume_summary}

I admire {company}'s ongoing innovation and would welcome the opportunity to discuss how my skill set and enthusiasm can add immediate value to your engineering team.

My resume is attached for your consideration. I look forward to connecting!

Best regards,
{applicant}
"""
    return {
        "subject": subject,
        "body": body.strip(),
        "to_email": hr_email,
        "company": company,
    }


def send_referral_email_direct(
    to_email: str,
    subject: str,
    body: str,
    resume_path: str = None
) -> dict:
    """
    Send an email referral request or direct HR application via configured SMTP.
    """
    if not auto_apply.is_valid_email(to_email):
        raise auto_apply.InvalidApplicationError(f"Invalid recipient email address: '{to_email}'")

    pdf_path = resume_path or os.getenv("RESUME_PDF_PATH")
    auto_apply.send_application_email(
        to_email=to_email,
        subject=subject,
        body=body,
        resume_path=pdf_path
    )
    return {
        "status": "sent",
        "to": to_email,
        "subject": subject,
        "has_attachment": bool(pdf_path and Path(pdf_path).is_file())
    }


if __name__ == "__main__":
    print("Testing Referral Email Generation...")
    sample = generate_google_referral_email(
        applicant_name="Anilkumar",
        job_title="Software Engineer - Backend",
        job_id_or_url="https://careers.google.com/jobs/results/12345",
        target_company="Google",
        referrer_name="Alex",
        top_skills=["Python", "FastAPI", "Distributed Systems", "MySQL"],
        access_type="public",
    )
    print("Subject:", sample["subject"])
    print("\nBody Preview:\n", sample["body"][:300], "...")
