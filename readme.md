# MASPY RAG API & LLM Agent Pipeline

An advanced **Retrieval-Augmented Generation (RAG)** infrastructure designed to generate, integrate, and audit code for the **MASPY** BDI agent framework.

This project uses Google Cloud Run to expose a FastAPI application that orchestrates a multi-agent LLM chain (Gemini 1.5 Flash) backed by a vector database (Pinecone).

## 🧠 Agent Pipeline Architecture

To ensure the generated MASPY code strictly adheres to BDI survival rules (separation of agents and environments, correct belief usage, and life-cycle management), the system implements an **LLM Chain** with three distinct roles:

1. **Architect Agent:** Retrieves context from Pinecone and designs the core BDI classes (Agents and Environments).
2. **Integrator Agent:** Receives the classes and builds the main execution block (`if __name__ == "__main__":`), managing the connection topology.
3. **Senior Reviewer Agent:** Inspects the final code for logical flaws (e.g., premature `stop_cycle()`, sending messages to environments) and returns the sanitized code.

## 📂 Project Structure

The repository is organized into the following main directories:

* **`app/`**: Contains the core FastAPI logic, RAG orchestration, and Gemini prompts.
* **`data/`**: Python (`.py`) files with MASPY code examples used to populate the vector database.
* **`scripts/`**: Independent utilities, including `ingest.py` to process and send embeddings to Pinecone.
* **`frontend/`**: Client application built with Next.js/React (`chat_rag/`) for graphical interaction with the API.
* **`backend/`**: Legacy logic and local integrations with the MASPY framework core (`codigos_maspy/`).
* **`runner/`**: Configurations (including a `Dockerfile`) for a secure execution sandbox for the generated code.

## 🛠️ Tech Stack

* **API Framework:** FastAPI (Python 3.11)
* **LLM & Embeddings:** Google Gemini 1.5 Flash & `models/embedding-001`
* **Orchestration:** LangChain
* **Vector Database:** Pinecone
* **Cloud Infrastructure:** Google Cloud Run, Cloud Build, Artifact Registry

## 🚀 Step-by-Step Local Setup

### 1. Prerequisites
Ensure Python 3.11+ is installed. Create a `.env` file in the root directory (ignored by Git) with your API keys:
```env
GOOGLE_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
```

### 2. Installation
Create a virtual environment and install the required dependencies:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Data Ingestion
Process the example files in the `data/` directory and send their embeddings to Pinecone:
```bash
python scripts/ingest.py
```

### 4. Running the API Locally
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`. Access the Swagger UI at `http://127.0.0.1:8000/docs` to test the endpoints.

## ☁️ Google Cloud Run Deployment

Deployment is handled via the Google Cloud CLI using the provided `Dockerfile`.

### 1. Authenticate and Setup
Authenticate your Google account and set your project:
```bash
gcloud init
```

### 2. Build and Deploy
Deploy the application directly from the source code:
```bash
gcloud run deploy maspy-rag-api --source . --region us-central1 --allow-unauthenticated
```

### 3. Inject Environment Variables
Securely inject your API keys into the active Cloud Run service:
```bash
gcloud run services update maspy-rag-api --update-env-vars GOOGLE_API_KEY="your_api_key",PINECONE_API_KEY="your_api_key" --region us-central1
```

## 📝 API Usage Example

**Endpoint:** `POST /chat`

**Payload:**
```json
{
  "pergunta": "Create a Thermostat agent that turns on the heater when the Room environment sends a cold percept."
}
```

**Response:**
A JSON object containing the fully structured, audited Python code ready to be executed by the MASPY framework.