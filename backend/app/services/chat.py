import os
from typing import List, Dict, Any
from google import genai
from google.genai import types
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient

# Import definitions
from app.models.chat import ChatResponse, Citation, RAGResponse

# Simple In-Memory History
SESSION_HISTORY: Dict[str, List[Dict[str, str]]] = {}

class ChatService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        
        # 1. Initialize Qdrant Client (Native)
        self.qdrant_url = os.getenv("QDRANT_HOST", "qdrant")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = "nyx_documents_v2"

        self._qdrant_client = QdrantClient(
            host=self.qdrant_url,
            port=self.qdrant_port
        )

        # 2. Initialize Vector Store (LangChain Wrapper for Retrieval)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            task_type="retrieval_query",
            google_api_key=self.api_key
        )

        self.vector_store = QdrantVectorStore(
            client=self._qdrant_client,
            collection_name=self.collection_name,
            embedding=self.embeddings
        )

        # 3. Initialize Google GenAI Client (The New SDK)
        self.genai_client = genai.Client(api_key=self.api_key)

        # 4. System Instruction
        self.system_instruction = """
        You are NYX, an expert AI analyst specializing in strict, evidence-based retrieval. 
        Your goal is to answer user questions using ONLY the provided context snippets.

        ### CORE DIRECTIVES (HIERARCHY OF TRUTH)
        1. **CONTEXT IS KING:** The information in the 'RETRIEVED CONTEXT' block is the absolute truth for this conversation. 
           - If the context says "The sky is neon green", then the sky is neon green. 
           - Ignore your pre-existing knowledge if it contradicts the context.
        2. **NO OUTSIDE KNOWLEDGE:** Do not fill in gaps with your own training data. If the answer isn't in the chunks, refuse to answer.
        3. **CITATION MANDATE:** Every single assertion must be backed by a specific 'source_id' from the context.

        ### RESPONSE PROCESS (CHAIN OF THOUGHT)
        Before answering, you must perform a structured analysis in the 'thinking_process' field:
        1. **Analyze the Request:** What specific facts is the user looking for?
        2. **Scan Context:** Look for keywords and semantic matches in the provided source chunks.
        3. **Verify Grounding:** Can the answer be constructed *exclusively* from these chunks?
        4. **Formulate/Refuse:** - If yes: Draft the answer citing IDs.
           - If no: Set 'is_refusal' to true and explain what is missing.

        ### FEW-SHOT EXAMPLES (EDGE CASES)

        **Case 1: The "Counter-Intuitive" Fact (Pokemon/Fiction Scenario)**
        *Context:* [ID: doc_1] "To catch a Legendary Pokemon, you must sing a lullaby into the microphone. Using Master Balls causes the game to crash."
        *User:* "Should I use a Master Ball on Mewtwo?"
        *Thought:* User asks about Master Ball usage. Common knowledge says yes, but Context [doc_1] explicitly says it crashes the game. I must follow Context.
        *Output:* {
            "thinking_process": "Context explicitly warns against Master Balls for Legendaries, contradicting standard game lore. I will enforce the context's rule.",
            "answer": "No, according to the document, using a Master Ball will cause the game to crash. You should instead sing a lullaby.",
            "citation_ids": ["doc_1"],
            "is_refusal": false
        }

        **Case 2: The "Missing Link" (Partial Information)**
        *Context:* [ID: policy_a] "Refunds are processed within 5 days." [ID: policy_b] "Only manager approval allows exceptions."
        *User:* "What is the phone number for refunds?"
        *Thought:* Context mentions refund *timelines* and *approval*, but scans for "phone number" or "contact" yield zero matches. I cannot hallucinate a number.
        *Output:*
        {
            "thinking_process": "The user wants a contact method (phone). The provided chunks discuss timelines and permissions, but contain no contact details.",
            "answer": "I cannot find a phone number for refunds in the provided documents. The text only specifies processing times and approval rules.",
            "citation_ids": [],
            "is_refusal": true
        }

        **Case 3: The "Explicit Inference" (Safe Deduction)**
        *Context:* [ID: report_9] "Project Alpha failed due to lack of budget."
        *User:* "Was Project Alpha successful?"
        *Thought:* The text doesn't say "No", but it says "failed". "Failed" is the antonym of "successful". This is a valid linguistic deduction, not an external hallucination.
        *Output:*
        {
            "thinking_process": "User asks about success. Source [report_9] states the project 'failed'. I can confirm it was not successful.",
            "answer": "No, Project Alpha was not successful; the documents state it failed due to budget constraints.",
            "citation_ids": ["report_9"],
            "is_refusal": false
        }
        """

    def _get_history_text(self, session_id: str) -> str:
        """Formats history as a text block for the prompt."""
        history = SESSION_HISTORY.get(session_id, [])[-5:] # Last 5 turns
        text_hist = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            text_hist += f"{role}: {msg['content']}\n"
        return text_hist

    def _update_history(self, session_id: str, user_msg: str, ai_msg: str):
        if session_id not in SESSION_HISTORY:
            SESSION_HISTORY[session_id] = []
        SESSION_HISTORY[session_id].append({"role": "user", "content": user_msg})
        SESSION_HISTORY[session_id].append({"role": "model", "content": ai_msg})

    async def process_query(self, session_id: str, message: str) -> ChatResponse:
        """
        Main RAG Pipeline with DEBUGGING enabled
        """
        print(f"\n--- [DEBUG] Processing Query: {message} ---")
        try:
            # A. Retrieval
            docs_and_scores = self.vector_store.similarity_search_with_score(message, k=5)

            # B. Guardrail: Low Confidence Check
            best_score = docs_and_scores[0][1] if docs_and_scores else 0
            
            if not docs_and_scores:
                return ChatResponse(
                    answer="Error: No documents found in database. Did you upload a file?",
                    citations=[],
                    is_refusal=True,
                    session_id=session_id
                )

            # C. Format Context & Map Citations
            context_str = ""
            citation_map = {} 

            for doc, score in docs_and_scores:
                chunk_ref_id = f"{doc.metadata.get('file_hash', 'unk')}_{doc.metadata.get('chunk_id', '0')}"
                context_str += f"\n--- Source ID: {chunk_ref_id} ---\n{doc.page_content}\n"
                citation_map[chunk_ref_id] = doc

            # D. Construct the Prompt
            history_text = self._get_history_text(session_id)
            
            full_prompt = f"""
            {self.system_instruction}

            CONVERSATION HISTORY:
            {history_text}

            RETRIEVED CONTEXT:
            {context_str}

            USER QUESTION: 
            {message}
            """

            # E. Generate Content
            print("--- [DEBUG] Sending request to Gemini-2.0-flash...")
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RAGResponse,
                    temperature=0.1
                )
            )

            rag_result: RAGResponse = response.parsed

            if not rag_result:
                raise ValueError("Empty response from LLM")

            # G. Reconstruct Citations
            final_citations = []
            if not rag_result.is_refusal:
                for ref_id in rag_result.citation_ids:
                    if ref_id in citation_map:
                        doc = citation_map[ref_id]
                        final_citations.append(Citation(
                            source_id=ref_id,
                            quote=doc.page_content[:150] + "...",
                            file_name=doc.metadata.get("filename", "Unknown"),
                            page=doc.metadata.get("page", None)
                        ))

            self._update_history(session_id, message, rag_result.answer)

            return ChatResponse(
                answer=rag_result.answer,
                citations=final_citations,
                is_refusal=rag_result.is_refusal,
                session_id=session_id
            )

        except Exception as e:
            print(f"--- [DEBUG] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return ChatResponse(
                answer=f"System Error: {str(e)}",
                citations=[],
                is_refusal=True,
                session_id=session_id
            )

# Singleton
chat_service = ChatService()