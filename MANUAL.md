# How to Run Property Guardian AI

## Prerequisites
1.  **Python 3.9+** installed.
2.  **PostgreSQL** installed and running.
3.  **Git** (optional, to clone the repo).

## Setup Steps

### 1. Database Setup
Ensure you have a Postgres database created. The default config expects:
-   **Database Name**: `property_db`
-   **User**: `postgres`
-   **Password**: `password` (or update `.env`)

If you haven't created the database yet, run this in your Postgres shell (SQL Shell or pgAdmin):
```sql
CREATE DATABASE property_db;
```

### 2. Configure Environment
Create a file named `.env` in the root folder (`rag/`) if it doesn't exist. Add your API keys and DB config:
```ini
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/property_db

# Keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=arcee-ai/trinity-large-preview:free
```

### 3. Install Dependencies
Open your terminal (Command Prompt or PowerShell) in the `rag` folder and run:
```bash
pip install -r requirements.txt
```

## Running the App

### Start the Interface
Run the Streamlit application:
```bash
streamlit run streamlit_app.py
```
This will automatically open your browser to `http://localhost:8501`.

## Troubleshooting
-   **Database Error**: Check if Postgres is running and the `DATABASE_URL` in `.env` is correct.
-   **Dependency Error**: Try running `pip install --upgrade pip` then install requirements again.
-   **Browser doesn't open**: Manually visit `http://localhost:8501` in Chrome/Edge, etc.
