# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Evita criação de arquivos .pyc e força flush imediato de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Instala dependências do sistema mínimas se necessário
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root para execução segura
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Instala dependências Python em camada com cache otimizado
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY app/ ./app/

# Ajusta permissões
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck do container
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

