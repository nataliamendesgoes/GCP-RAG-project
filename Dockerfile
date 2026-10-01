# ---------- Etapa 1: gera o site estático (Next.js -> pasta out/) ----------
FROM node:22-slim AS site

WORKDIR /site

# Dependências primeiro (otimiza o cache do build)
COPY frontend/chat_rag/package.json frontend/chat_rag/package-lock.json ./
RUN npm ci

# Código do frontend; o build usa o .env.production (API em /api)
COPY frontend/chat_rag/ ./
RUN npm run build


# ---------- Etapa 2: API + site ----------
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY --from=site /site/out ./static

# O Cloud Run injeta a variável de ambiente $PORT (por padrão, 8080)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
