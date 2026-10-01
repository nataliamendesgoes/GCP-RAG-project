"""
Executa código de agentes MASPY gerado pelo LLM em processo isolado,
com proteção contra:
  - exceções normais (bugs de sintaxe/semântica)
  - não-terminação (loop de percepção-ação BDI sem condição de parada)
  - uso excessivo de memória/CPU (apenas em Linux/macOS — ver nota abaixo)

Funciona em Windows e em Linux/macOS. O mecanismo de matar o processo
"travado" é diferente em cada um:
  - Linux/macOS: grupo de processos (os.setsid + os.killpg)
  - Windows: grupo de processos do Windows (CREATE_NEW_PROCESS_GROUP) +
    `taskkill /T /F`, que mata a árvore de processos inteira

NOTA IMPORTANTE (Windows): o módulo `resource` (usado para limitar memória
via RLIMIT_AS) não existe no Windows. Nesta plataforma, o limite de memória
NÃO é aplicado — a única proteção é o timeout. Se isso for um requisito
forte pro seu experimento, a forma correta no Windows é usar Job Objects
via `pywin32` (bem mais código); posso montar isso se precisar.
"""

import os
import subprocess
import sys
import tempfile
import time
from typing import TypedDict

from .config import CONFIG

IS_WINDOWS = sys.platform == "win32"

if not IS_WINDOWS:
    import resource
    import signal


class SandboxResult(TypedDict):
    success: bool
    status: str        # "completed" | "timeout" | "os_error"
    stdout: str
    stderr: str
    runtime_seconds: float


def _limit_resources_unix(mem_limit_mb: int):
    """Executado no processo filho antes do exec (preexec_fn). Só em Linux/macOS."""
    def _inner():
        mem_bytes = mem_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        os.setsid()  # novo grupo de processos -> permite matar filhos/netos de uma vez
    return _inner


def run_in_sandbox(
    code_str: str,
    timeout: int = CONFIG.INNER_TIMEOUT_SECONDS,
    mem_limit_mb: int = CONFIG.INNER_MEM_LIMIT_MB,
) -> SandboxResult:
    """
    Executa `code_str` como um script Python isolado.

    Distingue explicitamente:
      - status="completed": o processo terminou sozinho (com ou sem erro)
      - status="timeout": foi morto à força por exceder o tempo limite
        (indica possível loop de percepção/ação sem terminação, comum
        em agentes BDI mal formados)
    """
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(code_str)
        path = f.name

    start = time.monotonic()
    proc = None
    try:
        proc = _spawn_process(path, mem_limit_mb)
        stdout, stderr = proc.communicate(timeout=timeout)
        return {
            "success": proc.returncode == 0,
            "status": "completed",
            "stdout": stdout,
            "stderr": stderr,
            "runtime_seconds": time.monotonic() - start,
        }

    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        stdout, stderr = proc.communicate()
        return {
            "success": False,
            "status": "timeout",
            "stdout": stdout,
            "stderr": stderr
            or "Agente excedeu o tempo limite (possível loop BDI sem condição de parada).",
            "runtime_seconds": time.monotonic() - start,
        }

    except OSError as e:
        return {
            "success": False,
            "status": "os_error",
            "stdout": "",
            "stderr": str(e),
            "runtime_seconds": time.monotonic() - start,
        }

    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _spawn_process(path: str, mem_limit_mb: int) -> subprocess.Popen:
    """Inicia o processo do script, já isolado em seu próprio grupo/árvore."""
    python_exe = sys.executable  # garante o mesmo interpretador (venv correto)

    if IS_WINDOWS:
        return subprocess.Popen(
            [python_exe, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    return subprocess.Popen(
        [python_exe, path],
        preexec_fn=_limit_resources_unix(mem_limit_mb),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _kill_process_tree(proc: subprocess.Popen):
    """Mata o processo E todos os filhos (SIGTERM/SIGKILL no Unix, taskkill no Windows)."""
    if proc is None or proc.pid is None:
        return

    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            text=True,
        )
        return

    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        time.sleep(1)
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # já morreu sozinho entre o timeout e a tentativa de kill