# interview_prep.py
# Generates comprehensive interview preparation questions with detailed ANSWER TIPS.
# Fixes the issue: "Interview prep -> Questions raise -> Answer tips ❌"
# Provides answer tips (key points, STAR framework, sample phrases, pitfalls to avoid)
# using Gemini AI with intelligent domain fallback.
import json
import os
import re

try:
    import ai_analyzer
except ImportError:
    ai_analyzer = None


FALLBACK_QUESTION_BANK = [
    {
        "id": 1,
        "category": "Technical Architecture",
        "question": "How do you design scalable RESTful APIs using Python and FastAPI, and how do you ensure high performance?",
        "answer_tips": {
            "key_points": [
                "Mention asynchronous request handling using async/await and ASGI servers (Uvicorn).",
                "Explain Pydantic schemas for strict request/response data validation and serialization.",
                "Discuss database connection pooling and query optimization (indexes, pagination).",
                "Highlight caching strategies (Redis / in-memory cache) and middleware for CORS and logging."
            ],
            "star_framework": {
                "situation": "Describe a project where you built or refactored an API with growing traffic.",
                "task": "Explain your goal: minimize latency and prevent database bottlenecks.",
                "action": "Detail how you implemented async FastAPI endpoints, indexing, and connection pools.",
                "result": "State measurable outcomes (e.g. 50% faster response times, handled 10x traffic)."
            },
            "sample_answer_points": "In FastAPI, I leverage native async endpoints alongside connection pooling. For example, instead of querying the database synchronously on every request, I implement pagination and indexed queries, cutting latency to under 50ms.",
            "pitfalls_to_avoid": "Avoid blocking I/O calls inside async def functions. Don't omit input validation or error handling."
        }
    },
    {
        "id": 2,
        "category": "Database & Data Modeling",
        "question": "How do you approach database schema design, indexing, and transaction safety in MySQL?",
        "answer_tips": {
            "key_points": [
                "Explain normalization (3NF) to reduce redundancy vs deliberate denormalization for read performance.",
                "Describe composite indexes for multi-column search queries and checking execution plans with EXPLAIN.",
                "Discuss ACID transactions, foreign keys, and rollbacks during error conditions.",
                "Mention connection safety: always closing connections or using context managers."
            ],
            "star_framework": {
                "situation": "A backend application experienced slow queries as data volume grew.",
                "task": "Analyze the bottlenecks and optimize schema and queries.",
                "action": "Used EXPLAIN to identify full table scans, added composite B-Tree indexes, and wrapped updates in transactions.",
                "result": "Query execution dropped from 1.8s to 15ms with 0 locked table timeouts."
            },
            "sample_answer_points": "I ensure schema design aligns with primary read/write patterns. For frequent queries with filters, I inspect query plans using EXPLAIN and create targeted indexes while keeping transactions concise to avoid row locking.",
            "pitfalls_to_avoid": "Avoid over-indexing write-heavy tables, and never leave uncommitted open transactions."
        }
    },
    {
        "id": 3,
        "category": "Behavioral & STAR",
        "question": "Tell me about a time you encountered a difficult technical bug under time pressure. How did you resolve it?",
        "answer_tips": {
            "key_points": [
                "Clearly structure using STAR (Situation, Task, Action, Result).",
                "Focus on systematic root cause analysis rather than random guesswork.",
                "Demonstrate composure, clear communication with teammates, and post-mortem prevention.",
                "Showcase the automated test or monitoring you added so the bug never repeats."
            ],
            "star_framework": {
                "situation": "During a release, automated applications were failing intermittently due to timeout errors.",
                "task": "Identify root cause without disrupting active users.",
                "action": "Isolated logs, reproduced the issue locally, identified unclosed database cursors, and added automated regression tests.",
                "result": "Resolved within 45 minutes with 100% test coverage and zero data loss."
            },
            "sample_answer_points": "When diagnosing issues under pressure, I start by reviewing error logs and isolating the minimal reproduction case. Once resolved, I write automated unit tests to prevent regressions.",
            "pitfalls_to_avoid": "Don't blame teammates or tools. Don't claim you 'just guessed and it worked'."
        }
    },
    {
        "id": 4,
        "category": "AI Integration & Automation",
        "question": "How do you handle rate limits, hallucinations, and fallback handling when integrating LLMs (like Google Gemini) into production apps?",
        "answer_tips": {
            "key_points": [
                "Strict JSON schema enforcement using response_mime_type: 'application/json'.",
                "Multi-model fallback tiers (e.g. gemini-2.0-flash -> gemini-1.5-flash -> local keyword analyzer).",
                "Exponential backoff and retry logic for transient 429/503 errors.",
                "Prompt guardrails: treating inputs as data rather than instructions to prevent prompt injection."
            ],
            "star_framework": {
                "situation": "Building an AI-driven resume and job matching engine.",
                "task": "Ensure the system stays 100% operational even if the AI API is unavailable or rate-limited.",
                "action": "Designed a graceful degradation pipeline: Gemini AI primary, keyword parser secondary fallback.",
                "result": "99.9% uptime with zero user-facing crashes during API outages."
            },
            "sample_answer_points": "I implement multi-tier fallbacks: if the AI service encounters an error or missing key, the application seamlessly switches to a rule-based analyzer without failing the user's request.",
            "pitfalls_to_avoid": "Never expose raw API keys in client-side code or unhandled exception traces."
        }
    },
    {
        "id": 5,
        "category": "Full Stack & Frontend Integration",
        "question": "How do you coordinate state, asynchronous API communication, and error feedback between a web frontend and backend?",
        "answer_tips": {
            "key_points": [
                "Consistent API response contracts (HTTP status codes: 200, 422, 404, 500).",
                "Clear visual loading states and disabled submit buttons during pending requests.",
                "Graceful error banners displaying human-friendly messages instead of raw crash traces.",
                "CORS security configuration allowing only designated origins."
            ],
            "star_framework": {
                "situation": "Users experienced silent failures when submitting long resumes.",
                "task": "Provide instant feedback, progress indication, and clear validation errors.",
                "action": "Implemented async/await fetch with try-catch blocks, animated status indicators, and clean toast alerts.",
                "result": "User confusion dropped by 80% with positive usability reviews."
            },
            "sample_answer_points": "I design clear contracts between client and server. The client handles loading and error states smoothly, while the backend returns standardized JSON error details.",
            "pitfalls_to_avoid": "Don't leave the UI frozen without a spinner or disabled button during network requests."
        }
    }
]


def generate_interview_prep(job_title: str, job_description: str = "", resume_text: str = "") -> dict:
    """
    Generate tailored interview questions accompanied by rich ANSWER TIPS for each question.
    Uses Google GenAI if configured, or the curated high-quality interview question bank.
    """
    title = (job_title or "Software Engineer").strip()
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key and ai_analyzer is not None:
        try:
            client = ai_analyzer.get_client()
            prompt = f"""
You are an expert technical interviewer and career coach.
Generate 5 comprehensive interview questions for the role: "{title}".
For EACH question, you MUST provide detailed "answer_tips".

Job Description:
{job_description[:2000] if job_description else "Focus on core engineering, system architecture, database, problem solving, and leadership."}

Candidate Resume Context:
{resume_text[:2000] if resume_text else "General engineering candidate."}

Return strictly valid JSON with this exact structure:
{{
  "role": "{title}",
  "total_questions": 5,
  "questions": [
    {{
      "id": 1,
      "category": "Technical Architecture | Coding & Algorithm | Behavioral & STAR | Role Specific",
      "question": "The interview question",
      "answer_tips": {{
        "key_points": ["Key point 1 to mention", "Key point 2 to mention"],
        "star_framework": {{
          "situation": "How to frame the situation",
          "task": "What task to describe",
          "action": "What specific action to highlight",
          "result": "What measurable result to emphasize"
        }},
        "sample_answer_points": "A concrete talking phrase or sample answer snippet",
        "pitfalls_to_avoid": "Common mistake or red flag to avoid"
      }}
    }}
  ]
}}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            if "questions" in data and len(data["questions"]) > 0:
                data["source"] = "gemini"
                return data
        except Exception:
            pass  # Fallback to curated question bank

    # Curated fallback with rich answer tips customized for the requested role
    customized_questions = []
    for idx, q in enumerate(FALLBACK_QUESTION_BANK, 1):
        item = dict(q)
        item["id"] = idx
        if idx == 1 and title.lower() != "software engineer":
            item["question"] = f"In your role as a {title}, how do you architect core systems and ensure reliability under load?"
        customized_questions.append(item)

    return {
        "role": title,
        "total_questions": len(customized_questions),
        "source": "curated_bank",
        "questions": customized_questions,
        "note": "Complete with detailed Answer Tips, STAR framework, and sample phrases."
    }


if __name__ == "__main__":
    print("Testing Interview Prep Generator with Answer Tips...")
    prep = generate_interview_prep("Python Backend Developer")
    print(f"Role: {prep['role']}, Total Questions: {prep['total_questions']}")
    for q in prep["questions"]:
        print(f"\n[{q['category']}] Q: {q['question']}")
        print(f"  -> Key Points: {q['answer_tips']['key_points'][0]}")
        print(f"  -> Pitfall to Avoid: {q['answer_tips']['pitfalls_to_avoid']}")
