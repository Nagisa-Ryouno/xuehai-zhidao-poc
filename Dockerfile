# 学海智导后端 · 云端部署镜像
# 用法（Render/Railway/自有服务器通用）：
#   docker build -t xuehai-api .
#   docker run -p 8011:8011 xuehai-api
# Render 部署时 startCommand 会被 render.yaml 中的 $PORT 版本覆盖
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8011

CMD ["uvicorn", "gateway.api:app", "--host", "0.0.0.0", "--port", "8011"]
