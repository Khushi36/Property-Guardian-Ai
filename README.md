# Property Guardian AI 🛡️

Property Guardian AI is an advanced, AI-powered system designed to secure property ownership and detect fraudulent transactions. By combining structured data analysis in PostgreSQL with vector-based semantic search in ChromaDB and relationship analysis in Neo4j, it provides a comprehensive security audit for property portfolios.

## 🚀 Key Features

- **Deep Security Audit**: Automatically detects "Broken Chain of Title" and "Double Selling" anomalies using advanced SQL window functions.
- **Neo4j Graph Explorer**: Visualize the historical chain-of-title and track multiple transactions visually across buyers, sellers, and documents.
- **AI-Powered Querying**: Consult with an AI assistant about property regulations and transaction history using natural language, backed by RAG.
- **Smart Ingestion**: Upload property deeds (PDF), automatically extract ownership metadata, and instantly sync nodes to the graph database.
- **Fraud Analytics**: Visualize high-risk properties and transaction patterns in real-time on the dashboard.
- **Developer Tools**: Execute safe, strictly parsed read-only SQL queries via a built-in interactive dashboard.

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) for a sleek, responsive dashboard.
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) for high-performance service orchestration.
- **Infrastructure** (Orchestrated securely via Docker): 
  - **PostgreSQL**: Stores structured property and transaction records.
  - **ChromaDB**: Handles vector embeddings for semantic document search.
  - **Neo4j**: Native Graph Database for deep transaction-chain visualization.
  - **Redis**: Fast caching and aggressive API rate-limiting via SlowAPI.
- **AI Engine**: Advanced LLM models via OpenRouter for intelligent data extraction and logical querying.

---

## ⚙️ Setup & Installation (Step-by-Step)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Khushi36/Property-Guardian-Ai.git
cd Property-Guardian-Ai
```

### Step 2 — Configure the `.env` File

Copy the `.env.example` file to create your own configuration.

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Ensure your `.env` has these core values populated (you MUST provide `SECRET_KEY` and an `OPENROUTER_API_KEY`):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/property_db
SECRET_KEY=paste_a_secure_random_hex_string_here
OPENROUTER_API_KEY=sk-or-v1-...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=arcee-ai/trinity-large-preview:free

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
```

*(You can generate a secure SECRET_KEY in python using `import secrets; print(secrets.token_hex(32))`)*

### Step 3 — Start the Infrastructure (Docker Required)

The easiest and only supported way to run all 4 databases (Postgres, Neo4j, Redis, Chroma) reliably is through Docker. Ensure Docker Desktop is running, then execute:

```bash
docker compose up -d
```
*(Wait a few seconds for all containers to report 'Healthy')*

### Step 4 — Set up your Python Environment and Start Backend

In the root of the project:

```bash
# Create/activate virtual env
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows

# Install Dependencies
pip install -r requirements.txt

# Start Backend API
python main.py
```
*(The API will be available at http://localhost:8000)*

### Step 5 — Start the Frontend Application

Open a **new terminal tab**, activate your virtual environment, and run:

```bash
python -m streamlit run streamlit_app.py --server.port 8502
```

Navigate to **http://localhost:8502** in your browser. Register an account and begin!

---

## 🛑 Stopping the Application

- Press `Ctrl + C` in both backend and frontend terminal windows to halt the Python processes.
- Shut down all your databases safely with: `docker compose down`

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `SECRET_KEY Field required` error | Create a `.env` file with a valid `SECRET_KEY` (see Step 2) |
| `psycopg2` / DB connection refused | Ensure Docker containers are running (`docker compose ps`) |
| ChromaDB `WMI` Windows error | Disable telemetry. This is already handled in `.env.example` with `CHROMA_TELEMETRY=False`. |
| Port 8000/8502 already in use | Kill the background Python process or restart your terminal. |

---

## 📜 License

This project is licensed under the MIT License.
