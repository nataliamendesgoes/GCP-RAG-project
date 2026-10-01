# MASPY usa typing.override -> Python 3.12+
FROM python:3.12-slim

WORKDIR /runner

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Usuário sem privilégios para rodar o código dos visitantes
RUN useradd --create-home --uid 10001 executor
USER executor

# Uma execução por vez (concurrency 1 no Cloud Run); o $PORT vem do Cloud Run
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
