import os
from pathlib import Path
import requests
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import ResourceExhausted
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pydantic import BaseModel
from app.guardrails import verificar_pergunta
from app.rag_service import responder_pergunta

# Site estático (build do Next.js), copiado para a imagem pelo Dockerfile
SITE_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="MASPY RAG API",
    description="API RAG para o framework BDI MASPY utilizando Gemini e Pinecone",
    version="1.0.0"
)

# Em produção o site e a API têm a mesma origem, então o CORS só é usado no desenvolvimento
# (frontend em localhost:3000 chamando a API em localhost:8080)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

router = APIRouter(prefix="/api")

# Modelo de dados esperado na requisição
class QueryRequest(BaseModel):
    pergunta: str

class QueryResponse(BaseModel):
    resposta: str

@router.get("/")
def health_check():
    """Endpoint de verificação de saúde."""
    return {"status": "online", "service": "MASPY RAG API"}

@router.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    """Recebe uma pergunta, processa no RAG e devolve a resposta do Gemini."""
    if not request.pergunta.strip():
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")

    # Trava: pergunta fora do assunto é respondida aqui mesmo, sem chamar o Gemini
    recusa = verificar_pergunta(request.pergunta)
    if recusa:
        print(f"Pergunta barrada pela trava: {request.pergunta[:120]!r}")
        return {"resposta": recusa}

    try:
        resposta_gerada = responder_pergunta(request.pergunta)
        return {"resposta": resposta_gerada}

    except ResourceExhausted as e:
        print(f"Cota do Gemini esgotada: {e}")
        raise HTTPException(status_code=429, detail="Cota da API Gemini esgotada. Tente novamente mais tarde.")

    except Exception as e:
        # Imprime o erro no log do servidor (útil no GCP) e devolve 500
        print(f"Erro interno: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar a pergunta.")

# ---------- Execução do código (repassada ao serviço maspy-runner, que não tem chaves) ----------

# Local: http://localhost:8081 (sem autenticação). Cloud Run: URL https do runner, chamada com token de identidade
RUNNER_URL = os.environ.get("RUNNER_URL", "").rstrip("/")

class ExecRequest(BaseModel):
    codigo: str

@router.post("/executar")
def executar_endpoint(request: ExecRequest):
    """Executa o programa MASPY no runner isolado e devolve status, saída e erros."""
    if not RUNNER_URL:
        raise HTTPException(status_code=503, detail="Execução não configurada (RUNNER_URL).")
    if not request.codigo.strip():
        raise HTTPException(status_code=400, detail="Não há código para executar.")

    headers = {}
    if RUNNER_URL.startswith("https://"):
        # O runner só aceita chamadas autenticadas; a conta de serviço desta API tem o papel run.invoker nele
        headers["Authorization"] = f"Bearer {id_token.fetch_id_token(GoogleRequest(), RUNNER_URL)}"

    try:
        r = requests.post(f"{RUNNER_URL}/executar", json={"codigo": request.codigo}, headers=headers, timeout=60)
    except requests.RequestException as e:
        print(f"Runner indisponível: {e}")
        raise HTTPException(status_code=503, detail="O executor está indisponível. Tente novamente.")

    if r.status_code == 422:
        raise HTTPException(status_code=400, detail="Código grande demais para executar.")
    if r.status_code in (429, 503):
        raise HTTPException(status_code=503, detail="O executor está ocupado. Tente novamente em alguns segundos.")
    if not r.ok:
        print(f"Runner respondeu {r.status_code}: {r.text[:300]}")
        raise HTTPException(status_code=502, detail="Falha no executor.")
    return r.json()

app.include_router(router)

# O site entra por último: as rotas /api/... acima têm prioridade
if SITE_DIR.is_dir():
    app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
