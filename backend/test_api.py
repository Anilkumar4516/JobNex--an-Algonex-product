#test_api.py
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai

def run_test():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Note: GEMINI_API_KEY was not found in .env.")
        print("JobNex will automatically use its built-in smart fallback analyzer and career assistant.")
        return False

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly: Gemini API connection successful"
        )
        print("Gemini API connection successful!")
        print("Response:", response.text.strip())
        return True
    except Exception as error:
        print(f"Gemini API connection test note: {error}")
        return False


if __name__ == "__main__":
    run_test()