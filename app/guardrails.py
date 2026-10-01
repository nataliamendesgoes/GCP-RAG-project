"""
Travas do chat: barram perguntas fora do assunto ANTES de chamar o Gemini (sem custo).

Aceita a pergunta se ela tiver algum termo de sistemas multiagentes / MASPY. Termos
genéricos ("plano", "mensagem") deixam passar algumas perguntas fora do assunto; essas
são recusadas pela regra no prompt (rag_service.py), que é a segunda camada.
"""

import re
import unicodedata
from typing import Optional

# Marcador que o frontend coloca quando envia o código atual para ser alterado
MARCADOR_CODIGO = "codigo maspy atual"

TERMOS = [
    # Framework e paradigma
    "maspy", "bdi", "agente", "agentes", "agent", "agents", "multiagente", "multiagentes",
    "multi-agente", "multi agente", "multi-agent", "multiagent", "sma",
    # Estado mental
    "crenca", "crencas", "belief", "beliefs", "desejo", "desire", "intencao", "intencoes",
    "intention", "objetivo", "objetivos", "goal", "goals", "percept", "percepcao", "percepcoes",
    "perceber", "percebe",
    # Planos e API
    "plano", "planos", "plan", "plans", "@pl", "gain", "lose", "achieve", "tell", "untell",
    "askone", "askonereply", "askall", "tellhow", "stop_cycle", "start_system", "connect_to",
    # Ambiente e comunicação
    "ambiente", "ambientes", "environment", "channel", "canal", "canais", "admin",
    "mensagem", "mensagens", "comunicacao", "comunicar", "comunicam", "send", "broadcast",
    # Cenários clássicos de SMA (os exemplos do acervo)
    "negociacao", "negociar", "negociam", "leilao", "contract net", "contract-net", "protocolo",
    "comprador", "vendedor", "cruzamento", "semaforo", "estacionamento", "coletor", "robo", "robos",
]

# Expressões comuns que contêm os termos acima mas não são sobre agentes (removidas antes da busca)
FALSOS_POSITIVOS = [
    "meio ambiente", "plano de estudo", "plano de estudos", "plano de negocio", "plano de negocios",
    "plano de saude", "plano de aula", "plano de carreira", "plano de marketing", "objetivo de vida",
    "agente de viagem", "agente de viagens", "agente de saude", "agente secreto",
]

_PADRAO = re.compile(r"(?<![a-z0-9_])(" + "|".join(re.escape(t) for t in TERMOS) + r")(?![a-z0-9_])")

MENSAGEM_FORA_DO_ASSUNTO = (
    "Eu só consigo ajudar com **sistemas multiagentes em MASPy**. "
    "Descreva os agentes que você quer criar ou faça uma pergunta sobre o framework, por exemplo:\n\n"
    "- *Crie dois agentes que trocam mensagens entre si.*\n"
    "- *Como um agente reage a uma crença nova?*"
)


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para 'crença' e 'crenca' contarem igual."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


def verificar_pergunta(pergunta: str) -> Optional[str]:
    """Devolve a mensagem de recusa, ou None se a pergunta pode seguir para o Gemini."""
    normalizado = _normalizar(pergunta.strip())
    if MARCADOR_CODIGO in normalizado:
        return None  # pedido de alteração do código gerado: sempre está no assunto
    for expressao in FALSOS_POSITIVOS:
        normalizado = normalizado.replace(expressao, " ")
    if _PADRAO.search(normalizado):
        return None
    return MENSAGEM_FORA_DO_ASSUNTO
