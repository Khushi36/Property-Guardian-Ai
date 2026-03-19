# Property Guardian AI 🛡️

Property Guardian AI is an advanced, AI-powered system designed to secure property ownership and detect fraudulent transactions. By combining structured data analysis in PostgreSQL with vector-based semantic search in ChromaDB, it provides a comprehensive security audit for property portfolios.

## 🚀 Key Features

- **Deep Security Audit**: Automatically detects "Broken Chain of Title" and "Double Selling" anomalies using advanced SQL window functions.
- **AI-Powered Querying**: Consult with an AI assistant about property regulations and transaction history using natural language.
- **Smart Ingestion**: Upload property deeds (PDF) and automatically extract and index ownership data.
- **Voice Interaction**: Ask questions using your voice with integrated Speech-to-Text (STT).
- **Multilingual Support**: Freely query the system in English, Hindi, Marathi, and other supported languages.
- **Fraud Analytics**: Visualize high-risk properties and transaction patterns in real-time.

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) for a sleek, responsive dashboard.
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) for high-performance service orchestration.
- **Database**: 
  - **PostgreSQL**: Stores structured property and transaction records.
  - **ChromaDB**: Handles vector embeddings for semantic document search.
- **AI Engine**: Advanced LLM models (via OpenRouter) for intelligent data extraction and querying.
- **Infrastructure**: Docker & Docker Compose for seamless deployment.

## 📋 Prerequisites

Before you begin, make sure you have the following installed on your machine:

| Requirement | Version | Check Command |
|---|---|---|
| **Python** | 3.11+ | `python --version` |
| **PostgreSQL** | 14+ | `psql --version` |
| **pip** | Latest | `pip --version` |
| **Git** | Any | `git --version` |

You will also need a free **LLM API Key** from [OpenRouter](https://openrouter.ai/) (sign up → Dashboard → API Keys → Create Key).

---

## ⚙️ Setup & Installation (Step-by-Step)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Khushi36/Property-Guardian-Ai.git
cd Property-Guardian-Ai
```

### Step 2 — Create a Virtual Environment (Recommended)

```bash
# Create the virtual environment
python -m venv .venv

# Activate it
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Windows (CMD):
.venv\Scripts\activate.bat

# On macOS/Linux:
source .venv/bin/activate
```

You should see `(.venv)` at the beginning of your terminal prompt after activation.

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> ⏳ This may take 2–5 minutes on the first run as it downloads all packages.

### Step 4 — Set Up PostgreSQL Database

Make sure PostgreSQL is running, then create the database:

```bash
# Open the PostgreSQL shell
psql -U postgres

# Inside the psql shell, run:
CREATE DATABASE property_db;
\q
```

> 💡 Replace `postgres` with your PostgreSQL username if different.

### Step 5 — Configure the `.env` File

1. **Copy the example file:**
   ```bash
   # Windows:
   copy .env.example .env

   # macOS/Linux:
   cp .env.example .env
   ```

2. **Generate a SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output string.

3. **Edit the `.env` file** with your values:
   ```env
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/property_db
   SECRET_KEY=paste_your_generated_hex_string_here
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
   LLM_BASE_URL=https://openrouter.ai/api/v1
   LLM_MODEL=arcee-ai/trinity-large-preview:free
   ```

> ⚠️ **Important:** `SECRET_KEY` and `DATABASE_URL` are **required**. The app will not start without them.

### Step 6 — Initialize the Database Tables

```bash
python init_db.py
```

**Expected output:**
```
Starting database initialization...
SUCCESS: Database tables created at localhost:5432/property_db
```

---

## 🏃 Running the Application

You need **two terminal windows** — one for the backend and one for the frontend.

### Terminal 1 — Start the Backend API

```bash
python main.py
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to stop)
```

Verify by visiting: **http://localhost:8000/health**

### Terminal 2 — Start the Frontend UI

Open a **new terminal**, activate the venv again, then run:

```bash
# Activate venv (if not active)
.venv\Scripts\Activate.ps1    # Windows
source .venv/bin/activate      # macOS/Linux

# Start the frontend
streamlit run streamlit_app.py
```

**Expected output:**
```
Local URL: http://localhost:8501
```

### Open the App

Open your browser and go to: **http://localhost:8501**

### Default User Credentials

| Email | Password |
|---|---|
| `admin@example.com` | `password` |
| `user@example.com` | `password` |

---

## 🐳 Running with Docker (Alternative)

```bash
docker-compose up --build
```

---

## 🛑 Stopping the Application

Press `Ctrl + C` in each terminal window to stop the backend and frontend.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `SECRET_KEY Field required` error | Create a `.env` file with a valid `SECRET_KEY` (see Step 5) |
| `psycopg2` connection refused | Ensure PostgreSQL is running (`pg_isready` to check) |
| `ModuleNotFoundError` | Activate your venv and run `pip install -r requirements.txt` |
| Port 8000/8501 already in use | Kill the process using that port or change the port |

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
