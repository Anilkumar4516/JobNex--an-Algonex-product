# test_api.py
import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path for scripts and IDEs
_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

try:
    from google import genai  # type: ignore
except ImportError:
    genai = None  # type: ignore


def run_test() -> bool:
    # Explicitly load .env from backend folder if present
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.is_file():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Note: GEMINI_API_KEY was not found in .env.")
        print("JobNex will automatically use its built-in smart fallback analyzer and career assistant.")
        return False

    if genai is None:
        print("Note: 'google-genai' library is not installed in the active environment.")
        print("Run: pip install google-genai to enable live AI features.")
        return False

    try:
        client = genai.Client(api_key=api_key)
        # Try available Gemini flash models
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        last_error = None
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents="Reply with exactly: Gemini API connection successful"
                )
                resp_text = (getattr(response, "text", "") or "").strip()
                print(f"Gemini API connection successful using '{model_name}'!")
                if resp_text:
                    print("Response:", resp_text)
                return True
            except Exception as model_err:
                last_error = model_err
                continue

        if last_error:
            print(f"Gemini API connection note: {last_error}")
        return False
    except Exception as error:
        print(f"Gemini API connection test note: {error}")
        return False


if __name__ == "__main__":
    run_test()