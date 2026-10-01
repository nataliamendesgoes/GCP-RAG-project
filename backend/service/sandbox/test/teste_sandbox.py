"""
Testes de sanidade — não dependem do Ollama, só do sandbox_executor
e error_parser. Rode com: pytest sandbox/tests/
"""

import sys

import pytest

from sandbox.error_parser import parse_traceback
from sandbox.sandbox_executor import run_in_sandbox


def test_success_case():
    result = run_in_sandbox("print('ok')")
    assert result["success"] is True
    assert result["status"] == "completed"
    assert "ok" in result["stdout"]


def test_exception_case():
    result = run_in_sandbox("raise ValueError('erro proposital')")
    assert result["success"] is False
    assert result["status"] == "completed"
    info = parse_traceback(result["stderr"], status=result["status"])
    assert info["exception_type"] == "ValueError"
    assert "erro proposital" in info["message"]


def test_timeout_case():
    # loop infinito -> deve ser morto e classificado como timeout, não como crash
    result = run_in_sandbox("while True:\n    pass", timeout=2)
    assert result["success"] is False
    assert result["status"] == "timeout"
    info = parse_traceback(result["stderr"], status=result["status"])
    assert info["category"] == "timeout"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Limite de memória (RLIMIT_AS) não existe no Windows — só é aplicado em Linux/macOS.",
)
def test_memory_limit_case():
    # tenta alocar bem mais que o limite -> deve falhar, não travar
    code = "x = bytearray(500 * 1024 * 1024)"  # 500MB > limite de 256MB
    result = run_in_sandbox(code, mem_limit_mb=256, timeout=5)
    assert result["success"] is False
    assert result["status"] in ("completed", "timeout")
