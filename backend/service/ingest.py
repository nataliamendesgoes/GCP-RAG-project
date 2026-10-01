import os
import shutil
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===== Imports com Fallbacks =====
try:
    from langchain.schema import Document
except Exception:
    from langchain_core.documents import Document

try:
    from langchain_chroma import Chroma
except Exception:
    try:
        from langchain_community.vectorstores import Chroma
    except Exception:
        try:
            from langchain.vectorstores import Chroma
        except Exception:
            Chroma = None

try:
    from langchain_ollama import OllamaEmbeddings
except Exception:
    try:
        from langchain_community.embeddings import OllamaEmbeddings
    except Exception:
        try:
            from langchain.embeddings import OllamaEmbeddings
        except Exception:
            OllamaEmbeddings = None

try:
    from service.domain import detectar_entidades_no_codigo
except ImportError:
    def detectar_entidades_no_codigo(x): return []

from service.config import (
    SOURCE_DIR, EMBEDDING_DIR, EMBEDDING_MODEL, OLLAMA_BASE_URL
)


def main():
    print("--- INGESTÃO MASPY (arquivos completos) ---")

    missing = []
    if Chroma is None:
        missing.append("Chroma")
    if OllamaEmbeddings is None:
        missing.append("OllamaEmbeddings")

    if missing:
        print(f"❌ ERRO: Dependências ausentes: {', '.join(missing)}")
        print("   Execute: pip install -r requirements.txt")
        return

    #  Limpeza do banco antigo
    if os.path.exists(EMBEDDING_DIR):
        print("🗑️  Removendo banco antigo...")
        try:
            shutil.rmtree(EMBEDDING_DIR)
        except Exception as e:
            print(f"⚠️  Não foi possível apagar automaticamente: {e}")

    #  Lê cada arquivo .py como um Document completo, nào faz representação por linha para manter o contexto completo do código, essencial para a compreensão de estruturas e relações entre entidades. O conteúdo é enriquecido com metadados, incluindo o caminho do arquivo e as entidades MASPY detectadas, para facilitar buscas futuras e análises contextuais.
    print(f"📂 Lendo arquivos de: {SOURCE_DIR}")
    docs = []

    for root, _, files in os.walk(SOURCE_DIR):
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    conteudo = f.read().strip()
                if not conteudo:
                    continue
                doc = Document(
                    page_content=conteudo,
                    metadata={"source": fpath, "filename": fname}
                )
                docs.append(doc)
                print(f"   ✔ {fname} ({len(conteudo)} chars)")
            except Exception as e:
                print(f"   ⚠️  Erro ao ler {fname}: {e}")

    print(f"\n📄 {len(docs)} arquivos carregados.")

    # Enriquecimento de metadados com entidades MASPY detectadas, para facilitar buscas futuras e análises contextuais. O sistema de detecção de entidades é baseado em regras e padrões comuns encontrados nos códigos MASPY, como a presença de certos métodos, atributos ou estruturas de código que indicam a utilização de conceitos específicos do framework. As entidades detectadas são armazenadas como uma string separada por vírgulas no campo "maspy_entities" dos metadados de cada documento, permitindo uma fácil consulta e filtragem com base nessas entidades no futuro. Além disso, é gerada uma estatística simples das entidades detectadas em todos os documentos, mostrando quantos arquivos contêm cada entidade, o que pode ser útil para entender a prevalência de certos conceitos ou práticas dentro do código analisado.
    stats = {}
    for doc in docs:
        entidades = detectar_entidades_no_codigo(doc.page_content)
        if entidades:
            doc.metadata["maspy_entities"] = ",".join(entidades)
            for ent in entidades:
                stats[ent] = stats.get(ent, 0) + 1

    print("\n📊 Entidades detectadas:")
    for ent, count in sorted(stats.items()):
        print(f"   - {ent}: {count} arquivos")

    #  Salva no ChromaDB
    # Cada documento é o arquivo inteiro — o modelo recebe contexto completo
    print("\n💾 Salvando embeddings...")
    embedding_model = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL
    )

    Chroma.from_documents(
        documents=docs,
        embedding=embedding_model,
        persist_directory=EMBEDDING_DIR,
        collection_name="maspy_codes"
    )

    print(f"\n✅ Banco salvo em {EMBEDDING_DIR}")
    print(f"   {len(docs)} arquivos indexados como documentos completos.")


if __name__ == "__main__":
    main()