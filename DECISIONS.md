## Technical Stack and Language Choice

I chose **Python** as the primary language for the backend due to its unparalleled ecosystem for AI development and my personal proficiency with the language. This allowed me to implement complex logic—like semantic routing and custom ingestion pipelines—efficiently within the project's timeframe.

For orchestration, I opted for **LangChain** over LangGraph. While LangGraph offers powerful state-machine capabilities, I decided against it because the current requirements follow a linear, high-throughput RAG flow. Implementing a full graph-based architecture would have introduced significant boilerplate complexity that wasn't justified for this specific scope. However, for future iterations involving multi-agent negotiation or non-linear task solving, migrating to LangGraph would be the ideal path.

---

## 1. Vector Database: Qdrant

I selected **Qdrant** as the vector store for its robust native support for **metadata filtering**.

* **Reasoning:** Unlike simpler stores, Qdrant allows me to perform precise document retrieval using specific IDs (like my composite `file_hash_chunk_id`). This directly powers the **Evidence Inspector**, ensuring that when a user clicks a citation, the system retrieves the exact raw text snippet used for that specific answer.
* **Architecture:** I used the Rust-powered Qdrant engine inside a Docker container to ensure high-speed similarity searches with minimal resource overhead.

---

## 2. Chunking Strategy: Recursive Character Splitting

I implemented the **RecursiveCharacterTextSplitter** with a chunk size of **1000 characters** and an overlap of **200 characters**.

* **Semantic Coherence:** I avoided fixed-size splitting because it often cuts sentences in half, destroying the semantic link between ideas. Recursive splitting respects paragraph and sentence boundaries.
* **The "Pokemon" Edge Case:** This strategy was vital for passing my counter-intuitive lore tests. By keeping related sentences together, the LLM had enough context to realize that "The sky is neon green" was a fact within the document, successfully overriding its internal training.

---

## 3. Incremental Ingestion: MD5 Hashing

To fulfill the requirement for incremental ingestion, I built a custom **Deduplication Service** using **MD5 hashing**.

* **The Process:** Before any document is processed, I calculate a hash of its binary content. I store these hashes in a persistent SQLite database.
* **Efficiency:** If I detect a hash that already exists, I skip the expensive embedding and indexing steps entirely. This saves both compute time and API costs.

---

## 4. Implemented Guardrails

I built two primary guardrail mechanisms to ensure the RAG system remains grounded and secure:

* **Semantic Intent Router:** I used a lightweight LLM call as a "pre-check" tool. It classifies inputs as **Greeting**, **Security Risk**, or **RAG Query**. This prevents the system from hallucinating answers to chitchat or falling for prompt injections like "Ignore your instructions."
* **Chain of Thought (CoT) Prompting:** I forced the LLM to output its `thinking_process` before the final answer. This forces the model to analyze the retrieved chunks first, significantly reducing the chance of generating an answer when information is missing.

---

## 5. Areas for Future Improvement

I identified several areas where the system could be further hardened, though they were not included in this initial version:

* **Async GenAI Calls:** I did not implement fully non-blocking asynchronous calls for the LLM because the current Google GenAI SDK is primarily synchronous. In a high-traffic production environment, I would wrap these calls in a thread pool to prevent blocking the event loop.
* **Persistent Session Store:** Chat history is currently stored in-memory. I chose this approach to keep the Docker stack simple for evaluation. For a distributed system, I would replace this with a **Redis** or **PostgreSQL** store to maintain state across multiple instances.
* **Hybrid Search:** While semantic search is powerful, it sometimes misses specific keywords. I would eventually implement a hybrid search combining **BM25** (keyword matching) with dense vector embeddings to improve retrieval precision for specific nomenclature.