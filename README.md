# Multi-Agent Stock Research System 📈🤖

An AI-powered, multi-agent financial research and debate platform. This system autonomously retrieves real-time market data, orchestrates a debate between AI agents (Bull vs. Bear), and presents a final balanced verdict evaluated by a Judge agent.

## 🚀 Key Features

*   **Multi-Agent Debate (LangGraph-inspired):** Agents take different roles:
    *   **🐂 Bull Agent:** Argues the best-case scenario for the stock.
    *   **🐻 Bear Agent:** Argues the worst-case scenario.
    *   **👨‍⚖️ Judge Agent:** Weighs the evidence and outputs a final, unbiased verdict.
    *   **👨‍🔬 Experts:** Specialized agents for Fundamentals, Valuation, and Risk analysis.
    *   **😈 Devil's Advocate:** Challenges the Judge's verdict to ensure robustness.
*   **RAG & Context Assembly:** Hybrid retrieval (BM25 + Vector Search via `pgvector`) over news, financial filings, and analyst forecasts. It also pulls macro regime data (Fed Funds, 10Y Treasury, VIX) from FRED.
*   **Compliance & Verification Engine:** NLI-based citation checking and strict rule-based compliance filters to prevent unsuitable financial advice and hallucinated guarantees. Includes an immutable audit log.
*   **Bitemporal Data Ingestion:** Robust data pipelines for prices (yfinance), news (NewsAPI, RSS), filings (SEC EDGAR), and forecasts, cached in Redis and permanently stored in Postgres.

## 🏗️ Architecture (The 6-Person Division)

The codebase is cleanly divided into components originally designed as a 6-person team effort:
1.  **Data & Ingestion (`ingestion/`):** Fetches and normalizes data (Postgres + Redis).
2.  **RAG & Context (`intelligence/`):** Embeddings, hybrid search, and Context Assembler (Contract B).
3.  **Agent Orchestration (`orchestration/`):** Async DAG runner managing the debate flow.
4.  **LLM & Prompts (`models/`, `prompts/`):** LLM Gateway (Groq API) and detailed system prompts.
5.  **Verifier & Compliance (`compliance/`):** Citation verification, disclaimers, and audit logs.
6.  **API & Frontend (`api/`, `frontend/`):** FastAPI backend and Streamlit interactive UI.

## 🛠️ Prerequisites

*   **Docker** & **Docker Compose** (for Postgres with pgvector and Redis)
*   **Python 3.12+**
*   **Groq API Key** (for LLMs)

## 🚦 How to Run

### 1. Start the Databases
Ensure Docker is running, then start the Postgres and Redis containers:
```bash
docker compose up -d
```

### 2. Set Up the Environment
Make sure you have your `.env` file in the root directory with the necessary keys:
```env
GROQ_API_KEY=your_api_key_here
POSTGRES_USER=copilot
POSTGRES_PASSWORD=copilot
POSTGRES_DB=copilot
```

Install the dependencies:
```bash
pip install -r ingestion/requirements.txt
pip install fastapi uvicorn streamlit httpx
```

### 3. Run the Backend API
Start the FastAPI server on port 8001 (to avoid conflict with Docker):
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

### 4. Run the Frontend UI
In a separate terminal, start the Streamlit app:
```bash
python -m streamlit run frontend/app.py
```

Open your browser and navigate to `http://localhost:8501`.

## 🛡️ Disclaimer
This project is an AI-generated research demo for educational purposes only. It is **NOT** financial advice. Always consult a qualified financial advisor before making investment decisions.
