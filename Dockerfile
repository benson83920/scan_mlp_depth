FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# 建立專用的 log 目錄
RUN mkdir -p /app/logs

# 標記 /app/logs 為一個 volume（在容器啟動時可以掛載到 host 上）
VOLUME ["/app/logs"]

CMD ["python3", "main.py"]