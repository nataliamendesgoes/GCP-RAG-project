import re

# ==============================================================================
# ENTIDADES DO DOMÍNIO MASPY
# ==============================================================================
# Cobertura expandida para os 22 exemplos do acervo:
# askOneReply, buying-trip, contract-net, cruzamento, garbage-cleaner,
# hello-world, learn-*, move-boxes, parking, sample-messages,
# send-recv, simple-negotiation, simple-system, take-insert,
# traffic-light, Map_Env, Pygame_Screens, Walker_Ag

MASPY_ENTITIES = {
    "Plan": {
        "keywords": [
            "plano", "plan", "@pl", "gatilho", "trigger",
            "acao", "comportamento", "reagir", "executar",
        ],
        "regex": [r"@pl", r"Plan"]
    },
    "Agent": {
        "keywords": [
            "agente", "agent", "criacao", "setup", "start",
            "classe", "walker", "ambiente", "environment",
        ],
        "regex": [r"class\s+\w+\(Agent\):", r"super\(\)\.__init__"]
    },
    "Communication": {
        "keywords": [
            # Português
            "mensagem", "enviar", "receber", "comunicacao", "comunica",
            "responde", "responder", "solicita", "solicitar", "notifica",
            "pergunta", "pede", "manda", "avisa", "consulta", "consultar",
            "negocia", "negociar", "proposta", "contrato", "leilao",
            # Inglês (aparece nos exemplos)
            "send", "receive", "msg", "message", "reply", "notify",
            "ask", "negotiate", "contract", "auction", "bid",
        ],
        "regex": [
            r"self\.send\s*\(",
            r"self\.send\(src",
            r"achieve\s*,\s*Goal",
            r"tell\s*,\s*Belief",
            r"askOneReply",
            r"askOne\b",
        ]
    },
    "Belief_Goal": {
        "keywords": [
            "crenca", "belief", "objetivo", "goal", "estado", "mental",
            "desejo", "intencao", "sabe", "quer", "conhece", "percebe",
            "insert", "take", "aprender", "learn",
        ],
        "regex": [r"Belief\(", r"Goal\(", r"add_belief", r"add_goal"]
    },
    "Output": {
        "keywords": [
            "print", "log", "saida", "escrever", "mostrar",
            "exibir", "imprime", "display", "tela", "pygame",
        ],
        "regex": [r"self\.print", r"logger", r"pygame"]
    },
    "Environment": {
        "keywords": [
            "ambiente", "environment", "mapa", "map", "grid",
            "posicao", "position", "mover", "move", "andar",
            "cruzamento", "transito", "traffic", "parking", "estacionamento",
        ],
        "regex": [
            r"class\s+\w+\(Environment\):",
            r"Map_Env",
            r"Walker_Ag",
            r"pygame",
        ]
    }
}


def detectar_entidades_no_codigo(codigo_chunk: str) -> list:
    """
    Analisa um trecho de código e retorna tags das entidades MASPY presentes.
    Exemplo de retorno: ['Plan', 'Communication', 'Belief_Goal']
    """
    found_entities = set()
    for entity, rules in MASPY_ENTITIES.items():
        for pattern in rules["regex"]:
            if re.search(pattern, codigo_chunk, re.IGNORECASE):
                found_entities.add(entity)
                break

    if not found_entities:
        found_entities.add("General")

    return list(found_entities)


def detectar_intencao_na_pergunta(pergunta: str) -> list:
    """
    Analisa a pergunta do usuário e estima quais entidades MASPY ele precisa.
    Retorna lista de entidades, ex: ['Communication', 'Belief_Goal']
    """
    intencoes = set()
    pergunta_lower = pergunta.lower()

    for entity, rules in MASPY_ENTITIES.items():
        for kw in rules["keywords"]:
            if kw in pergunta_lower:
                intencoes.add(entity)
                break

    return list(intencoes)