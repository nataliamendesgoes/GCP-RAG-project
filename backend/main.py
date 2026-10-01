from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os

# Raiz do projeto IC (um nível acima de backend/)
IC_PATH = os.environ.get("IC_PATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, IC_PATH)
sys.path.insert(0, os.path.join(IC_PATH, "backend"))

app = FastAPI(
    title="MASPy Code Generator API",
    description="API REST para geração de código MASPy via sistema multiagentes com RAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: Optional[list[str]] = []

class HealthResponse(BaseModel):
    status: str
    message: str


# --- Componentes do pipeline (lazy, carregados na primeira requisição) ---

_components = None

def get_components():
    global _components
    if _components is None:
        try:
            from langchain_chroma import Chroma
        except Exception:
            from langchain_community.vectorstores import Chroma

        try:
            from langchain_ollama import OllamaLLM as ChatOllama, OllamaEmbeddings
        except Exception:
            from langchain_community.llms import Ollama as ChatOllama
            from langchain_community.embeddings import OllamaEmbeddings

        from service.config import EMBEDDING_DIR, LLM_MODEL, EMBEDDING_MODEL, OLLAMA_BASE_URL
        try:
            from service.config import REVISOR_MODEL
        except ImportError:
            REVISOR_MODEL = LLM_MODEL

        from service.retriever import MaspyEntityRetriever

        llm_gerador = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
        llm_revisor = ChatOllama(model=REVISOR_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.0)
        emb = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
        vs = Chroma(
            collection_name="maspy_codes",
            embedding_function=emb,
            persist_directory=EMBEDDING_DIR,
        )
        retriever = MaspyEntityRetriever(vectorstore=vs, search_kwargs={"k": 3})

        _components = {
            "llm_gerador": llm_gerador,
            "llm_revisor": llm_revisor,
            "retriever": retriever,
        }

    return _components


# --- Endpoints ---

@app.get("/", response_model=HealthResponse)
def root():
    return {"status": "ok", "message": "MASPy Code Generator API está rodando."}


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "message": "Serviço saudável."}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode ser vazia.")

    try:
        from service.chat import (
            MaspySanitizer,
            extract_code_block,
            extract_main_only,
            prompt_agente_arquiteto,
            prompt_agente_integrador,
            prompt_agente_revisor,
        )

        components = get_components()
        llm_gerador = components["llm_gerador"]
        llm_revisor = components["llm_revisor"]
        retriever   = components["retriever"]
        query       = request.message

        # 1. Recupera contexto RAG
        docs    = retriever.invoke(query)
        context = "\n\n".join([d.page_content for d in docs])
        sources = [d.metadata.get("source", "desconhecido") for d in docs]

        # 2. Agente Arquiteto — gera as classes
        res_classes  = llm_gerador.invoke(prompt_agente_arquiteto(query, context))
        classes_code = extract_code_block(
            res_classes.content if hasattr(res_classes, "content") else str(res_classes)
        )
        if "if __name__" in classes_code:
            classes_code = classes_code.split("if __name__")[0].strip()

        # 3. Agente Integrador — gera o bloco main
        res_main  = llm_gerador.invoke(prompt_agente_integrador(query, classes_code))
        main_code = extract_main_only(
            res_main.content if hasattr(res_main, "content") else str(res_main)
        )

        raw_combined = f"{classes_code}\n\n{main_code}"

        # 4. Agente Revisor — audita o código combinado
        res_revisor   = llm_revisor.invoke(prompt_agente_revisor(query, raw_combined))
        reviewed_code = extract_code_block(
            res_revisor.content if hasattr(res_revisor, "content") else str(res_revisor)
        )

        # 5. Sanitizador — pós-processamento final
        final_code = MaspySanitizer(reviewed_code).execute_pipeline()

        return ChatResponse(
            answer=f"```python\n{final_code}\n```",
            session_id=request.session_id or "default",
            sources=sources,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na geração: {str(e)}")