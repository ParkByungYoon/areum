FROM python:3.11-slim

WORKDIR /app

# Node.js 설치
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# React 빌드
COPY frontend/ frontend/
RUN cd frontend && npm install && npm run build

# 앱 소스
COPY . .

CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
