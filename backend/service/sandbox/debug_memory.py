"""
Acumula o histórico de tentativas fracassadas entre ciclos de
regeneração completa (loop externo), formatando-o como contexto
para o próximo prompt do Agente Arquiteto.
"""

from dataclasses import dataclass, field

from .config import CONFIG
from .error_parser import ErrorInfo


@dataclass
class DebugCycle:
    code: str
    errors: list[ErrorInfo]


@dataclass
class DebugMemory:
    cycles: list[DebugCycle] = field(default_factory=list)

    def add_cycle(self, code: str, errors: list[ErrorInfo]) -> None:
        self.cycles.append(DebugCycle(code=code, errors=errors))

    def to_context(self, max_cycles: int = CONFIG.OUTER_MEMORY_MAX_CYCLES) -> str:
        """Formata os últimos `max_cycles` ciclos como texto para o prompt do Arquiteto."""
        if not self.cycles:
            return ""

        blocks = []
        for i, cycle in enumerate(self.cycles[-max_cycles:], start=1):
            erros_resumidos = "; ".join(
                f"{e['exception_type']} ({e['category']}): {e['message']}"
                for e in cycle.errors
            )
            blocks.append(
                f"--- Tentativa anterior {i} (FALHOU) ---\n"
                f"Código gerado:\n{cycle.code}\n\n"
                f"Erros encontrados mesmo após correções locais:\n{erros_resumidos}\n"
            )
        return "\n".join(blocks)

    def to_serializable(self) -> list[dict]:
        """Formato pronto para json.dump — usado no logging estruturado."""
        return [
            {
                "code": c.code,
                "errors": c.errors,
            }
            for c in self.cycles
        ]