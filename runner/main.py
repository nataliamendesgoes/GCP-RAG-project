"""
Executor de código MASPY (serviço separado no Cloud Run: maspy-runner).

Roda o programa gerado em um subprocesso isolado, com tempo limite, e devolve a saída.
Este serviço NÃO tem chaves nem permissões no projeto: é seguro executar código
desconhecido aqui, ao contrário da API principal (que guarda as chaves do Gemini/Pinecone).
"""

import os
import re
import signal
import subprocess
import sys
import tempfile
import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

TEMPO_LIMITE_S = int(os.environ.get("TEMPO_LIMITE_S", "15"))  # agentes BDI podem nunca parar; a 1ª execução de uma instância nova carrega pandas/numpy (~8 s)
MAX_CODIGO = 20_000   # caracteres
MAX_SAIDA = 20_000    # caracteres devolvidos (stdout e stderr, cada)

ANSI = re.compile(r"\x1b\[[0-9;]*m")  # códigos de cor do terminal

app = FastAPI(title="MASPY Runner")


class ExecRequest(BaseModel):
    codigo: str = Field(min_length=1, max_length=MAX_CODIGO)


class ExecResponse(BaseModel):
    status: str        # "concluido" | "erro" | "tempo_esgotado"
    saida: str
    erro: str
    duracao_s: float


def _limpar(texto: str, arquivo: str, manter_cores: bool = False) -> str:
    texto = (texto or "").replace(arquivo, "maspy_system.py")  # esconde a pasta temporária
    if not manter_cores:
        texto = ANSI.sub("", texto)
    if len(texto) > MAX_SAIDA:
        texto = texto[:MAX_SAIDA] + "\n… (saída cortada)"
    return texto


def _matar(proc: subprocess.Popen) -> None:
    """Mata o processo e, no Linux, todo o grupo (caso o código crie subprocessos)."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError):
        pass


@app.get("/")
def health():
    return {"status": "online", "service": "MASPY Runner"}


@app.post("/executar", response_model=ExecResponse)
def executar(req: ExecRequest):
    # Pasta temporária própria: o MASPY grava logs/ no diretório atual
    with tempfile.TemporaryDirectory() as pasta:
        arquivo = os.path.join(pasta, "maspy_system.py")
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write(req.codigo)

        # Ambiente mínimo: nada do ambiente do serviço é herdado pelo código executado
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": pasta,
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "OPENBLAS_NUM_THREADS": "1",
            **({"SYSTEMROOT": os.environ["SYSTEMROOT"]} if "SYSTEMROOT" in os.environ else {}),  # Windows (teste local)
        }

        inicio = time.monotonic()
        proc = subprocess.Popen(
            [sys.executable, "-u", arquivo],
            cwd=pasta,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=(os.name == "posix"),
        )
        try:
            saida, erro = proc.communicate(timeout=TEMPO_LIMITE_S)
            status = "concluido" if proc.returncode == 0 else "erro"
        except subprocess.TimeoutExpired:
            _matar(proc)
            saida, erro = proc.communicate()
            status = "tempo_esgotado"

        return ExecResponse(
            status=status,
            # O MASPY colore cada linha com a cor do agente; o site converte os códigos nas mesmas cores do terminal
            saida=_limpar(saida, arquivo, manter_cores=True),
            erro=_limpar(erro, arquivo),
            duracao_s=round(time.monotonic() - inicio, 2),
        )
