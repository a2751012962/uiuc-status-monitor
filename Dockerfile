FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码到镜像中
COPY . .

# 暴露 8080 端口 (Fly.io 默认端口)
EXPOSE 8080

# 启动命令
# --workers 1: 单个 worker 进程，避免 split-brain (多实例数据不一致) 问题
# --threads 8: 8 个线程处理并发请求
# --timeout 120: 超时时间设置为 120 秒
# app:app: 启动 app.py 中的 app 对象
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]
