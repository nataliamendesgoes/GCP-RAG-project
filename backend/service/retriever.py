import os
from typing import List

try:
    from langchain.retrievers.base import BaseRetriever
except Exception:
    from langchain_core.retrievers import BaseRetriever

try:
    from langchain.callbacks.manager import CallbackManagerForRetrieverRun
except Exception:
    from langchain_core.callbacks import CallbackManagerForRetrieverRun

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

from service.domain import detectar_intencao_na_pergunta

# Arquivos que ensinam padrões ruins ou não têm relação com comunicação entre agentes
BLACKLIST = {
    "Pygame_Screens.py",
    "Map_Env.py",
}


class MaspyEntityRetriever(BaseRetriever):
    """
    Retriever para arquivos MASPY completos.

    Com arquivos inteiros no banco (não chunks), cada documento já tem
    o código completo com classes, planos e __main__. O re-ranking por
    entidade garante que o exemplo mais relevante para a query apareça primeiro.
    """

    vectorstore: Chroma
    search_kwargs: dict = {"k": 3}

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:

        k = self.search_kwargs.get("k", 3)

        intencoes = detectar_intencao_na_pergunta(query)
        intencoes_set = set(intencoes)
        print(f"🔍 [Retriever] Intenções: {list(intencoes_set)}")

        # Busca semântica ampla
        candidatos = self.vectorstore.similarity_search(query, k=k * 4)

        # Filtra blacklist
        candidatos = [
            d for d in candidatos
            if os.path.basename(d.metadata.get("source", "")) not in BLACKLIST
        ]

        if not intencoes_set:
            final = candidatos[:k]
            _log(final)
            return final

        # Re-ranking por entidade
        match_total   = []
        match_parcial = []
        sem_match     = []
        general       = []

        for doc in candidatos:
            entidades = set(doc.metadata.get("maspy_entities", "").split(","))
            if entidades == {"General"}:
                general.append(doc)
            elif intencoes_set.issubset(entidades):
                match_total.append(doc)
            elif intencoes_set & entidades:
                match_parcial.append(doc)
            else:
                sem_match.append(doc)

        resultado = match_total + match_parcial + sem_match + general

        if not resultado:
            resultado = candidatos

        final = resultado[:k]
        _log(final)
        return final


def _log(docs: List) -> None:
    fontes = [os.path.basename(d.metadata.get("source", "?")) for d in docs]
    print(f"✅ [Retriever] Selecionados: {fontes}")