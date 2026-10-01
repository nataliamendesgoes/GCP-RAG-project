import os
import sys
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore

# Raiz do projeto no sys.path para importar o pacote app/ ao rodar `python scripts/ingest.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.domain import detectar_entidades_no_codigo
from app.embeddings import criar_embeddings

load_dotenv()

# Configurações
SOURCE_DIR = "./data" # Os seus códigos .py devem estar aqui
NOME_DO_INDICE = "rag-docs" # O nome exato do seu banco no Pinecone

def main():
    print("--- INGESTÃO MASPY (Ficheiros Completos) no Pinecone ---")

    if not os.path.exists(SOURCE_DIR):
        print(f"❌ A pasta {SOURCE_DIR} não existe. Crie a pasta e coloque os ficheiros .py dentro.")
        return

    print(f"📂 A ler ficheiros de: {SOURCE_DIR}")
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
                
                # Cria o documento nativo do LangChain Core
                doc = Document(
                    page_content=conteudo,
                    metadata={"source": fpath, "filename": fname}
                )
                docs.append(doc)
                print(f"   ✔ {fname} ({len(conteudo)} caracteres)")
            except Exception as e:
                print(f"   ⚠️ Erro ao ler {fname}: {e}")

    if not docs:
        print("❌ Nenhum ficheiro .py válido encontrado para ingestão.")
        return

    print(f"\n📄 {len(docs)} ficheiros carregados.")

    # Enriquecimento com as entidades do seu domain.py
    stats = {}
    for doc in docs:
        entidades = detectar_entidades_no_codigo(doc.page_content)
        if entidades:
            doc.metadata["maspy_entities"] = entidades  # lista: o filtro $in do rag_service compara por elemento
            for ent in entidades:
                stats[ent] = stats.get(ent, 0) + 1

    print("\n📊 Entidades detetadas:")
    for ent, count in sorted(stats.items()):
        print(f"   - {ent}: {count} ficheiros")

    print("\n💾 A gerar embeddings e a enviar para a nuvem...")
    embedding_model = criar_embeddings()

    # Envia para o Pinecone
    PineconeVectorStore.from_documents(
        documents=docs,
        embedding=embedding_model,
        index_name=NOME_DO_INDICE
    )

    print("\n✅ Banco guardado no Pinecone com sucesso!")
    print(f"   {len(docs)} ficheiros indexados como documentos completos.")

if __name__ == "__main__":
    main()