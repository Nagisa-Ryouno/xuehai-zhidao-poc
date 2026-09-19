# 学海智导 · 云端一体化镜像（前端构建 + 后端 + 静态托管 + API 代理）
# 单容器 = 前端构建产物 + Python 后端 + 同端口静态服务与 /api 代理
# Render 会以 Docker 方式构建并把流量注入 $PORT

# ---- 阶段 1：构建前端 ----
FROM node:20-slim AS fe
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 阶段 2：后端运行 + 单进程一体化服务 ----
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=fe /fe/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 10000

CMD ["python", "scripts/serve_cloud.py"]
