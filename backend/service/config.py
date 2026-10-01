import os

# Pega o diretório base (raiz do projeto IC_PESQ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Onde estão os códigos fonte (Input)
SOURCE_DIR = os.path.join(BASE_DIR, "codigos_maspy/examples")

# Onde o banco vetorial e os documentos pais serão salvos (Output)
EMBEDDING_DIR = os.path.join(BASE_DIR, "embedding", "chroma_db")
DOCSTORE_DIR = os.path.join(BASE_DIR, "embedding", "doc_store")

# --- CONFIGURAÇÕES DO OLLAMA ---
# URL padrão do servidor local Ollama
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# Modelo de Geração (Chat): CodeLlama
LLM_MODEL = "qwen2.5-coder:7b"
REVISOR_MODEL = "llama3"

# Modelo de Embedding (Busca): BGE-M3
# Este modelo é MULTILÍNGUE, excelente para conectar perguntas em PT com código em EN.
EMBEDDING_MODEL = "bge-m3"