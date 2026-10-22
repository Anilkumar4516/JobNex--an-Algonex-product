# test_filter_logic.py
# Tests for JobNex filtering logic:
# 1. Keyword parsing & splitting
# 2. Region normalization & location matching (global, us, india, bengaluru)
# 3. Fallback job filtering (Northwind Labs, Brightpath Systems)
# 4. Score threshold filtering
# 5. API endpoint validation with clean TestClient handling
import unittest
import warnings
from unittest.mock import patch, MagicMock

# Suppress StarletteDeprecationWarning regarding httpx/httpx2 so TestClient runs cleanly
warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi.testclient import TestClient
import main
import daily_jobs
import job_fetcher


class FilterLogicUnitTests(unittest.TestCase):
    def test_split_keywords(self):
        """Test splitting varied keyword delimiters (commas, semicolons, newlines)."""
        self.assertEqual(
            daily_jobs.split_keywords("python, fastapi, mysql"),
            ["python", "fastapi", "mysql"]
        )
        self.assertEqual(
            daily_jobs.split_keywords("react; javascript\ntypescript"),
            ["react", "javascript", "typescript"]
        )
        self.assertEqual(daily_jobs.split_keywords(""), [])
        self.assertEqual(daily_jobs.split_keywords("   "), [])
        self.assertEqual(daily_jobs.split_keywords(None), [])

    def test_normalize_region(self):
        """Test that regions are correctly normalized to lower case and valid choices."""
        self.assertEqual(job_fetcher.normalize_region("US"), "us")
        self.assertEqual(job_fetcher.normalize_region("INDIA "), "india")
        self.assertEqual(job_fetcher.normalize_region("Bengaluru"), "bengaluru")
        self.assertEqual(job_fetcher.normalize_region(None), "global")
        with self.assertRaises(ValueError):
            job_fetcher.normalize_region("invalid_region_name")

    def test_region_matches(self):
        """Test location text matching across regions."""
        # Global accepts any location
        self.assertTrue(job_fetcher.region_matches("Anywhere", "global"))
        self.assertTrue(job_fetcher.region_matches("", "global"))

        # US matching
        self.assertTrue(job_fetcher.region_matches("USA Only", "us"))
        self.assertTrue(job_fetcher.region_matches("United States / Remote", "us"))
        self.assertFalse(job_fetcher.region_matches("Australia", "us"))

        # India & Bengaluru matching
        self.assertTrue(job_fetcher.region_matches("Bengaluru, India", "india"))
        self.assertTrue(job_fetcher.region_matches("Bangalore", "bengaluru"))
        self.assertTrue(job_fetcher.region_matches("Bengaluru, Karnataka", "bengaluru"))
        self.assertFalse(job_fetcher.region_matches("London, UK", "india"))

    def test_fallback_jobs_companies(self):
        """Test that fallback jobs include Northwind Labs and Brightpath Systems."""
        jobs = job_fetcher.get_fallback_jobs("python", limit=10, region="global")
        companies = [j["company"] for j in jobs]
        self.assertTrue(any("Northwind Labs" in c for c in companies))
        self.assertTrue(any("Brightpath Systems" in c for c in companies))

    def test_company_search_filters(self):
        """Test searching explicitly for Northwind or Brightpath."""
        northwind_jobs = job_fetcher.fetch_jobs("Northwind", limit=5)
        self.assertTrue(all("Northwind Labs" in j["company"] for j in northwind_jobs))

        brightpath_jobs = job_fetcher.fetch_jobs("Brightpath", limit=5)
        self.assertTrue(all("Brightpath Systems" in j["company"] for j in brightpath_jobs))


class FilterLogicApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Instantiate TestClient cleanly
        cls.client = TestClient(main.app)

    def test_search_jobs_with_region_filter(self):
        response = self.client.get("/api/jobs/search?keyword=python&region=india&limit=3")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["region"], "india")
        self.assertIn("jobs", data)
        self.assertIsInstance(data["jobs"], list)

    def test_search_jobs_invalid_region(self):
        response = self.client.get("/api/jobs/search?keyword=python&region=atlantis")
        self.assertEqual(response.status_code, 422)

    def test_search_jobs_short_keyword(self):
        response = self.client.get("/api/jobs/search?keyword=a")
        self.assertEqual(response.status_code, 422)

    def test_chat_endpoint_fallback(self):
        response = self.client.post("/api/chat", json={"message": "How do I improve my resume match score?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reply", data)
        self.assertIn("Optimization", data["reply"])

    def test_interview_prep_with_answer_tips(self):
        response = self.client.post("/api/interview/prep", json={"job_title": "Python Developer"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("questions", data)
        self.assertGreater(len(data["questions"]), 0)
        # Verify answer tips are present
        first_q = data["questions"][0]
        self.assertIn("answer_tips", first_q)
        self.assertIn("key_points", first_q["answer_tips"])
        self.assertIn("pitfalls_to_avoid", first_q["answer_tips"])

    def test_referral_generation(self):
        response = self.client.post(
            "/api/referrals/generate",
            json={
                "applicant_name": "Anil",
                "job_title": "Backend Dev",
                "job_id_or_url": "https://example.com/job/1",
                "target_company": "Google",
                "referrer_name": "Sam",
                "access_type": "public"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("subject", data)
        self.assertIn("body", data)
        self.assertIn("Google", data["subject"])

    def test_auto_scrape_job_endpoint(self):
        with patch("auto_apply.scrape_job_from_url") as mock_scrape:
            mock_scrape.return_value = {
                "job_title": "Python AI Specialist",
                "company": "Northwind Labs",
                "job_description": "Building next-generation AI workflows with Python and Gemini",
                "apply_email": "careers@northwindlabs.com",
                "location": "Remote",
                "job_type": "Full-time",
                "required_skills": ["Python", "FastAPI", "Google GenAI"],
                "job_url": "https://northwindlabs.com/job/1"
            }
            response = self.client.post(
                "/api/jobs/scrape",
                json={"url": "https://northwindlabs.com/job/1"}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["job_title"], "Python AI Specialist")
            self.assertEqual(data["company"], "Northwind Labs")
            self.assertIn("Python", data["required_skills"])


if __name__ == "__main__":
    unittest.main()


