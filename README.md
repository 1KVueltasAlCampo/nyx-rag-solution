# 🌌 NYX RAG Solution

### Advanced Retrieval-Augmented Generation System

NYX is a production-grade RAG engine built for the **Double V Partners Technical Challenge**. It features a structured semantic router, strict contextual grounding, and a transparent evidence-inspection pipeline.

---

## 🚀 Quick Start (Dockerized)

Ensure you have **Docker** and **Docker Compose** installed.

1. **Clone the repository:**
```bash
git clone <https://github.com/1KVueltasAlCampo/nyx-rag-solution>
cd nyx-rag-solution

```


2. **Configure Environment:**
Create a `.env` file in the root and add your Gemini API Key:
```bash
cp .env.example .env
# Edit .env and paste your GOOGLE_API_KEY

```


3. **Launch the Stack:**
```bash
docker-compose up --build

```


4. **Access the Application:**
* **Frontend UI:** `http://localhost:3000`
* **API Documentation (Swagger):** `http://localhost:8000/docs`
* **Health Check:** `http://localhost:8000/health`

---

## 🛠 Features & Engineering Philosophy

### 1. Semantic Intent Router (The "Gatekeeper")

Before hitting the vector database, NYX uses a **Lightweight Intent Classifier Tool**. It categorizes incoming messages into:

* **GREETING:** Fast-tracked response without vector search (cost-saving).
* **SECURITY_RISK:** Identifies and blocks prompt injections or adversarial attacks.
* **RAG_QUERY:** Standard retrieval flow for document-based questions.

### 2. Contextual Sovereignty (The "Pokemon" Case)

Traditional LLMs often hallucinate based on their training data. NYX implements **Strict Grounding Guardrails**.

> **Testing Case:** We tested the system with a "Counter-Intuitive Pokemon Guide" which claims that "Poké Balls are better than Master Balls for Legendaries." NYX successfully ignores its internal knowledge of Pokémon lore and answers strictly according to the uploaded document, proving the reliability of the grounding.

### 3. Incremental Ingestion

To avoid redundant processing and cost, NYX calculates a **Content Hash (MD5)** for every file. If a file with the same content is uploaded again, the system skips re-indexing.

### 4. Observability & Performance

Every RAG cycle is instrumented. You can see structured JSON logs in the backend console including:

* **LLM Inference Latency.**
* **Retrieval Scores.**
* **Component-specific success/error metrics.**

---

## 🎨 Frontend Walkthrough

The UI is designed as an **AI Operations Console**, divided into three functional areas:

* **Sidebar (Management):** Manage chat sessions (persisted in LocalStorage) and upload new documents.
* **Chat Area (Execution):** Conversational interface with multi-turn memory. Assistant responses include **Blue Citation Chips** (e.g., `[Document.pdf (p.1)]`).
* **Evidence Inspector (Transparency):** Clicking a citation chip slides out the right panel, which fetches the **Raw Content Chunk** directly from the Vector DB via the `/chunks` endpoint.

---

## 🧪 Integration Testing

The system includes a suite of **8 integration tests** covering the happy path, security risks, and the ingestion pipeline.

**Run tests within the Docker environment:**

```bash
docker exec -it nyx-backend python -m pytest tests/

```

---

## 📡 API Specification

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/v1/documents` | `POST` | Ingests PDF/Text with metadata and hash check. |
| `/api/v1/chat` | `POST` | Semantic Q&A with sessionId and Citations. |
| `/api/v1/chunks/{id}/{idx}` | `GET` | Retrieves raw text used as evidence. |
| `/health` | `GET` | Real-time diagnostic of API and Vector DB connection. |

---

## 🎥 Demo Video

[Watch the System in Action](https://drive.google.com/file/d/1zIDF_DChtdpkeN_5X_6PRIH40M6bjiB9/view?usp=sharing)