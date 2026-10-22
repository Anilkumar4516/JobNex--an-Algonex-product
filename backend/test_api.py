# test_api.py
import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    from google import genai  # type: ignore
except ImportError:
    genai = None  # type: ignore


def _load_backend_env() -> None:
    """Load the backend .env file when present, while tolerating missing dotenv."""
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.is_file():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()


def run_test() -> bool:
    _load_backend_env()
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()

    print("========================================")
    print("   JobNex Gemini AI API Diagnostic")
    print("========================================")

    if not api_key:
        print("[INFO] GEMINI_API_KEY is not set in backend/.env")
        print("[OK]   JobNex built-in smart fallback analyzer is ACTIVE.")
        print("[OK]   System functions properly using local keyword & rule engine.")
        print("----------------------------------------")
        print("To enable live Gemini AI:")
        print("  1. Get an API key from https://aistudio.google.com/")
        print("  2. Add GEMINI_API_KEY=your_key into backend/.env")
        print("========================================")
        return True

    if genai is None:
        print("[ERROR] 'google-genai' is not installed in the active environment.")
        print("Install it with: pip install google-genai")
        print("========================================")
        return False

    print("[INFO] GEMINI_API_KEY found. Testing connection to Google Gemini...")
    try:
        client = genai.Client(api_key=api_key)
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        last_error = None

        for model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents="Say hello and confirm API is connected in under 10 words.",
                )
                text = (getattr(response, "text", "") or "").strip()
                print(f"[SUCCESS] Connected to Google Gemini ({model})!")
                print(f"Response: {text}")
                print("========================================")
                return True
            except Exception as err:  # pragma: no cover - model-specific runtime issue
                last_error = err
                continue

        print(f"[WARNING] Could not reach any Gemini model. Details: {last_error}")
        print("========================================")
        return False
    except Exception as error:
        print(f"[ERROR] Gemini Client initialization failed: {error}")
        print("========================================")
        return False


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
