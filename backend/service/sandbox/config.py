"""
Configurações centrais do módulo de sandbox / self-debugging.
Ajuste aqui os hiperparâmetros que devem ser reportados no paper (WESAAC).

Reaproveita as constantes já definidas em service/config.py em vez de duplicá-las.
"""

import os
from dataclasses import dataclass

from service.config import BASE_DIR, OLLAMA_BASE_URL, LLM_MODEL

try:
    from service.config import REVISOR_MODEL
except ImportError:
    REVISOR_MODEL = LLM_MODEL

_DEFAULT_LOG_DIR = os.path.join(BASE_DIR, "logs", "self_debugging")


@dataclass(frozen=True)
class SandboxConfig:
    # --- Loop interno (correção local via Corretor, alimentado pelo erro real) ---
    INNER_TIMEOUT_SECONDS: int = 10          # tempo máximo por execução do agente MASPY
    INNER_MEM_LIMIT_MB: int = 256            # limite de memória por execução (RLIMIT_AS)
    INNER_MAX_ATTEMPTS: int = 3              # tentativas de correção local antes de escalar

    # --- Loop externo (regeneração completa a partir do Arquiteto) ---
    OUTER_MAX_CYCLES: int = 3                # regenerações completas antes de desistir
    OUTER_MEMORY_MAX_CYCLES: int = 3         # quantos ciclos de falha entram no contexto do Arquiteto

    # --- Timeout global por consulta do usuário ---
    GLOBAL_TIMEOUT_SECONDS: int = 300        # 5 min: protege contra loop BDI sem terminação

    # --- Diretórios (dentro do BASE_DIR do projeto) ---
    LOG_DIR: str = _DEFAULT_LOG_DIR          # onde salvar histórico JSON de cada rodada


CONFIG = SandboxConfig()