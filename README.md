# Property Guardian AI 🛡️

Property Guardian AI is an advanced, AI-powered system designed to secure property ownership and detect fraudulent transactions. By combining structured data analysis in PostgreSQL with vector-based semantic search in ChromaDB, it provides a comprehensive security audit for property portfolios.

## 🚀 Key Features

- **Deep Security Audit**: Automatically detects "Broken Chain of Title" and "Double Selling" anomalies using advanced SQL window functions.
- **AI-Powered Querying**: Consult with an AI assistant about property regulations and transaction history using natural language.
- **Smart Ingestion**: Upload property deeds (PDF) and automatically extract and index ownership data.
- **Fraud Analytics**: Visualize high-risk properties and transaction patterns in real-time.

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) for a sleek, responsive dashboard.
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/) for high-performance service orchestration.
- **Database**: 
  - **PostgreSQL**: Stores structured property and transaction records.
  - **ChromaDB**: Handles vector embeddings for semantic document search.
- **AI Engine**: Advanced LLM models (via OpenRouter/NVIDIA) for intelligent data extraction and querying.
- **Infrastructure**: Docker & Docker Compose for seamless deployment.

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 14+
- LLM API Key (e.g., [OpenRouter](https://openrouter.ai/))

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Khushi36/property-guardian-ai.git
cd property-guardian-ai
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/property_db
OPENROUTER_API_KEY=your_openrouter_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=arcee-ai/trinity-large-preview:free
SECRET_KEY=your_secret_key_here
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database
```bash
python init_db.py
```

## 🏃 Running the Application

### Option 1: Manual Start

**Start the Backend:**
```bash
python main.py
```

**Start the Frontend:**
```bash
streamlit run streamlit_app.py
```

### Option 2: Docker Compose (Recommended)
```bash
docker-compose up --build
```

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
