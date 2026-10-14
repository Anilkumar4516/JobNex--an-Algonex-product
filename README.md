# JobNex -- an Algonex product

JobNex is an AI-powered resume and job description analyzer backend built with FastAPI and MySQL, accompanied by an interactive frontend interface.

---

## 🛠️ Tech Stack
- **Backend:** Python, FastAPI, MySQL, Uvicorn
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)

---

## 🚀 Getting Started

### 1. Backend Setup
1. Open a terminal in the `backend/` folder:
   ```bash
   cd backend
   ```
2. Activate your virtual environment:
   ```powershell
   .\Algonex\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 2. Frontend Setup
Open `Frontend/index.html` in your browser or run with Live Server (port 5500 / 5501).
