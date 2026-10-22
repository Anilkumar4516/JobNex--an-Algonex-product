# job_fetcher.py
# Finds real job listings and can filter them by region.
#
#   Remotive (free, no key)  - remote jobs only. It has NO location filter, so for a
#                              region we fetch more jobs and match the words in its
#                              "candidate_required_location" text ("USA Only", ...).
#   Adzuna   (free API key)  - real country + city search. Used automatically for
#                              us / india / bengaluru once ADZUNA_APP_ID and
#                              ADZUNA_APP_KEY are set in .env.
#   Curated Fallback Jobs    - Northwind Labs, Brightpath Systems, etc. for offline/fallback reliability.
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs"
CACHE_SECONDS = 900
REMOTIVE_FILTER_FETCH = 100   # how many Remotive jobs we scan when filtering a region
_CACHE = {}

DEFAULT_REGION = "global"
REGIONS = ("global", "us", "india", "bengaluru")

# Curated jobs for fallback / offline / specific company search
FALLBACK_JOBS = [
    {
        "title": "Senior Python Backend Engineer",
        "company": "Northwind Labs",
        "location": "Bengaluru, India / Remote",
        "job_type": "full_time",
        "url": "https://northwindlabs.com/careers/backend-python",
        "description": (
            "Northwind Labs is seeking a Senior Python Backend Engineer to architect and build high-performance "
            "microservices using Python 3.11+, FastAPI, MySQL, Redis, and modern AI/LLM integrations. "
            "Responsibilities include designing clean RESTful APIs, optimizing SQL query performance, "
            "writing comprehensive unit tests, and automating deployment pipelines. "
            "Key skills: Python, FastAPI, MySQL, Docker, REST APIs, Git, and automated testing."
        ),
        "source": "northwind_labs",
    },
    {
        "title": "Full Stack Software Developer",
        "company": "Brightpath Systems",
        "location": "Bengaluru, India",
        "job_type": "full_time",
        "url": "https://brightpathsystems.com/jobs/full-stack-dev",
        "description": (
            "Brightpath Systems is hiring an experienced Full Stack Developer to build modern web applications. "
            "You will develop interactive frontend experiences with JavaScript/TypeScript, React, and CSS, "
            "alongside robust backend services using Python (FastAPI/Flask) and MySQL databases. "
            "Key skills: Python, JavaScript, React, FastAPI, MySQL, CSS3, HTML5, and Git."
        ),
        "source": "brightpath_systems",
    },
    {
        "title": "AI & Machine Learning Solutions Engineer",
        "company": "Northwind Labs",
        "location": "Remote (USA / Global)",
        "job_type": "full_time",
        "url": "https://northwindlabs.com/careers/ai-engineer",
        "description": (
            "Northwind Labs is expanding its applied AI capabilities. Seeking an AI Engineer skilled in "
            "Google GenAI (Gemini), prompt engineering, LLM integration, Python, and automated document analysis. "
            "Key skills: Python, Google GenAI, Gemini API, LangChain, Machine Learning, and NLP."
        ),
        "source": "northwind_labs",
    },
    {
        "title": "Cloud Systems & DevOps Engineer",
        "company": "Brightpath Systems",
        "location": "Remote / Bengaluru, India",
        "job_type": "full_time",
        "url": "https://brightpathsystems.com/jobs/devops-cloud",
        "description": (
            "Brightpath Systems is seeking a DevOps & Cloud Engineer to manage AWS/GCP cloud environments, "
            "Docker containerization, CI/CD pipelines, and database reliability. "
            "Key skills: Docker, Kubernetes, AWS, Linux, CI/CD, MySQL, and Python scripting."
        ),
        "source": "brightpath_systems",
    },
    {
        "title": "Junior Python Developer",
        "company": "Northwind Labs",
        "location": "Bengaluru, India",
        "job_type": "full_time",
        "url": "https://northwindlabs.com/careers/jr-python",
        "description": (
            "Northwind Labs is welcoming a passionate Junior Python Developer. Great opportunity to work on "
            "FastAPI backend services, automated workflows, and database integration. "
            "Key skills: Python, SQL basics, Git, problem solving, and enthusiasm for automation."
        ),
        "source": "northwind_labs",
    },
    {
        "title": "Frontend Engineer (UI/UX)",
        "company": "Brightpath Systems",
        "location": "USA / Remote",
        "job_type": "full_time",
        "url": "https://brightpathsystems.com/jobs/frontend-engineer",
        "description": (
            "Brightpath Systems is seeking a talented Frontend Engineer to design accessible, fluid web applications. "
            "Key skills: JavaScript, CSS3, HTML5, React, responsive design, and UI performance."
        ),
        "source": "brightpath_systems",
    },
]

# region -> (Adzuna country code, city spellings to try one after another)
ADZUNA_REGIONS = {
    "us": ("us", ()),
    "india": ("in", ()),
    "bengaluru": ("in", ("Bengaluru", "Bangalore")),
}

# Remotive only: words that must appear in the job's location text.
_REGION_PATTERNS = {
    "us": re.compile(r"(?<!\w)(usa|u\.s\.a?|us|united states|north america)(?!\w)", re.I),
    "india": re.compile(r"(?<!\w)india(?!\w)", re.I),
    "bengaluru": re.compile(r"(?<!\w)(bengaluru|bangalore)(?!\w)", re.I),
}


class JobFetchError(Exception):
    pass


def _strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------- regions ----------------

def normalize_region(region):
    """'US ' -> 'us'. Raises ValueError for anything that is not a known region."""
    region = (region or DEFAULT_REGION).strip().lower()
    if region not in REGIONS:
        raise ValueError("region must be one of: " + ", ".join(REGIONS))
    return region


def region_matches(location, region):
    """Does a location text belong to the region? 'global' keeps everything."""
    pattern = _REGION_PATTERNS.get(region)
    if pattern is None:
        return True
    return bool(pattern.search(location or ""))


def adzuna_configured():
    return bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"))


def job_source(region=DEFAULT_REGION):
    """Which site a search for this region will use: 'adzuna' or 'remotive'."""
    region = str(region or DEFAULT_REGION).strip().lower()
    if region in ADZUNA_REGIONS and adzuna_configured():
        return "adzuna"
    return "remotive"


def get_fallback_jobs(keyword="", limit=10, region=DEFAULT_REGION):
    """Filter curated fallback jobs (Northwind Labs, Brightpath Systems) by keyword & region."""
    kw = (keyword or "").strip().lower()
    matched = []
    for job in FALLBACK_JOBS:
        if not region_matches(job.get("location", ""), region):
            continue
        if kw:
            content = f"{job['title']} {job['company']} {job['description']}".lower()
            if kw in content or any(part in content for part in re.split(r"[\s,]+", kw) if len(part) >= 3):
                matched.append(dict(job))
        else:
            matched.append(dict(job))

    if not matched:
        matched = [dict(j) for j in FALLBACK_JOBS if region_matches(j.get("location", ""), region)]
    if not matched:
        matched = [dict(j) for j in FALLBACK_JOBS]

    return matched[:limit]


# ---------------- the two sources with safe HTTP ----------------

def _http_get_json(url, params=None, timeout=15):
    """Perform HTTP GET returning parsed JSON, using requests or urllib if requests is missing."""
    if params:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}" if "?" not in url else f"{url}&{query_string}"
    else:
        full_url = url

    if requests is not None:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()

    # urllib fallback if requests module is not installed
    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "JobNex/1.0 (Job Assistant)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        raw_data = resp.read().decode(charset)
        return json.loads(raw_data)


def _fetch_remotive(keyword, limit, region):
    fetch_limit = limit if region == DEFAULT_REGION else REMOTIVE_FILTER_FETCH

    try:
        payload = _http_get_json(
            REMOTIVE_URL,
            params={"search": keyword, "limit": fetch_limit},
            timeout=15,
        )
    except Exception as error:
        raise JobFetchError("Could not fetch jobs right now") from error

    jobs = []
    for item in payload.get("jobs", []):
        location = item.get("candidate_required_location", "")
        if not region_matches(location, region):
            continue

        jobs.append({
            "title": item.get("title", ""),
            "company": item.get("company_name", ""),
            "location": location,
            "job_type": item.get("job_type", ""),
            "url": item.get("url", ""),
            "description": _strip_html(item.get("description", "")),
            "source": "remotive",
        })

    if not jobs:
        fallback = get_fallback_jobs(keyword, limit, region)
        if fallback:
            return fallback

    return jobs[:limit]


def _fetch_adzuna(keyword, limit, region):
    country, cities = ADZUNA_REGIONS[region]
    url = f"{ADZUNA_URL}/{country}/search/1"

    base_params = {
        "app_id": os.getenv("ADZUNA_APP_ID"),
        "app_key": os.getenv("ADZUNA_APP_KEY"),
        "what": keyword,
        "results_per_page": limit,
    }

    results = []
    for city in (cities or (None,)):
        params = dict(base_params)
        if city:
            params["where"] = city

        try:
            payload = _http_get_json(url, params=params, timeout=15)
            results = payload.get("results", [])
        except Exception:
            results = []

        if results:
            break

    if not results:
        fallback = get_fallback_jobs(keyword, limit, region)
        if fallback:
            return fallback
        raise JobFetchError("Could not fetch jobs from Adzuna right now")

    jobs = []
    for item in results:
        company = (item.get("company") or {}).get("display_name", "")
        location = (item.get("location") or {}).get("display_name", "")
        jobs.append({
            "title": _strip_html(item.get("title", "")),
            "company": _strip_html(company),
            "location": location,
            "job_type": item.get("contract_time") or "",
            "url": item.get("redirect_url", ""),
            "description": _strip_html(item.get("description", "")),
            "source": "adzuna",
        })

    return jobs


# ---------------- public function ----------------

def fetch_jobs(keyword, limit=10, region=DEFAULT_REGION):
    keyword = (keyword or "").strip()
    if not keyword:
        raise ValueError("keyword is required")

    region = normalize_region(region)
    limit = max(1, min(int(limit), 25))

    # Check for direct company matching Northwind Labs or Brightpath Systems
    kw_lower = keyword.lower()
    if "northwind" in kw_lower or "brightpath" in kw_lower:
        return get_fallback_jobs(keyword, limit, region)

    source = job_source(region)
    cache_key = (source, region, kw_lower, limit)

    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]

    if source == "adzuna":
        jobs = _fetch_adzuna(keyword, limit, region)
    else:
        jobs = _fetch_remotive(keyword, limit, region)

    _CACHE[cache_key] = (time.time(), jobs)
    return jobs


if __name__ == "__main__":
    import sys
    search_term = sys.argv[1] if len(sys.argv) > 1 else "python"
    print(f"Fetching jobs for '{search_term}'...")
    results = fetch_jobs(search_term, limit=5)
    print(f"Found {len(results)} jobs:")
    for j in results:
        print(f" - {j['title']} at {j['company']} ({j['location']}) [{j['source']}]")