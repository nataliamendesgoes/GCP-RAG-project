from langchain_google_genai import GoogleGenerativeAIEmbeddings

MODELO_EMBEDDING = "models/gemini-embedding-001"
DIMENSAO_EMBEDDING = 768  # Deve ser igual à dimensão do índice no Pinecone


class GeminiEmbeddings768(GoogleGenerativeAIEmbeddings):
    """Força output_dimensionality, que o PineconeVectorStore não repassa (o padrão do Gemini é 3072)."""

    def embed_documents(self, texts, **kwargs):
        kwargs.setdefault("output_dimensionality", DIMENSAO_EMBEDDING)
        return super().embed_documents(texts, **kwargs)

    def embed_query(self, text, **kwargs):
        kwargs.setdefault("output_dimensionality", DIMENSAO_EMBEDDING)
        return super().embed_query(text, **kwargs)


def criar_embeddings() -> GeminiEmbeddings768:
    return GeminiEmbeddings768(model=MODELO_EMBEDDING)
