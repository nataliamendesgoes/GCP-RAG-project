"""
Extrai informação estruturada de falhas de execução, para alimentar
o Agente Corretor com um contexto mais útil do que o stderr cru.

Separa três categorias:
  - erro de sintaxe/exceção Python padrão
  - erro semântico específico do MASPY (crença/plano/objetivo mal formado)
  - timeout (não-terminação)
"""

import re
from typing import TypedDict

# Padrões conhecidos de erro do framework MASPY.
# Ajuste/expanda esta lista conforme forem aparecendo casos no seu dataset —
# vale documentar isso como parte da "taxonomia de erros" no paper.
MASPY_ERROR_PATTERNS = {
    r"belief.*not found|BeliefNotFoundError": "crença referenciada não existe no agente",
    r"plan.*not triggered|PlanNotFoundError": "nenhum plano corresponde ao evento/objetivo disparado",
    r"goal.*already.*achieved|GoalConflictError": "objetivo em conflito com estado atual de crenças",
    r"AgentSpeak|ASL.*parse": "erro de parsing na sintaxe de plano estilo AgentSpeak",
}


class ErrorInfo(TypedDict):
    category: str            # "python_exception" | "maspy_semantic" | "timeout" | "unknown"
    exception_type: str
    message: str
    maspy_hint: str          # explicação amigável se for erro conhecido do MASPY, senão ""
    raw_traceback: str


def parse_traceback(stderr: str, status: str = "completed") -> ErrorInfo:
    if status == "timeout":
        return {
            "category": "timeout",
            "exception_type": "TimeoutError",
            "message": "O agente não retornou dentro do tempo limite.",
            "maspy_hint": (
                "Verifique se há um plano com 'while True' (ou equivalente) sem "
                "condição de parada, ou uma espera bloqueante por evento/crença "
                "que nunca é satisfeita."
            ),
            "raw_traceback": stderr,
        }

    stderr = stderr.strip()
    lines = stderr.splitlines()
    exc_line = lines[-1] if lines else ""

    match = re.match(r"(\w+(?:Error|Exception)):\s*(.*)", exc_line)
    exception_type = match.group(1) if match else "UnknownError"
    message = match.group(2) if match else exc_line

    maspy_hint = ""
    category = "python_exception"
    for pattern, hint in MASPY_ERROR_PATTERNS.items():
        if re.search(pattern, stderr, re.IGNORECASE):
            maspy_hint = hint
            category = "maspy_semantic"
            break

    if not stderr:
        category = "unknown"
        exception_type = "UnknownError"
        message = "Falha sem stderr (verificar exit code / stdout)."

    return {
        "category": category,
        "exception_type": exception_type,
        "message": message,
        "maspy_hint": maspy_hint,
        "raw_traceback": stderr,
    }