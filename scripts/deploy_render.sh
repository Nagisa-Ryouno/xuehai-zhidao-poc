#!/usr/bin/env bash
# 学海智导 · Render 全自动部署脚本
# 用法：
#   export RENDER_API_KEY=rnd_xxxxxxxx
#   bash scripts/deploy_render.sh
set -e

REPO="https://github.com/guoda-design/xuehai-zhidao-poc"
BRANCH="feat/ui-enhancement"
SERVICE_NAME="xuehai-zhidao"

if [ -z "$RENDER_API_KEY" ]; then
  echo "请先设置 RENDER_API_KEY（Render Dashboard → Account Settings → API Keys）"
  exit 1
fi

AUTH="Authorization: Bearer $RENDER_API_KEY"
CT="Content-Type: application/json"
API="https://api.render.com/v1"

echo "== 查询账户 owner =="
OWNER=$(curl -sf -H "$AUTH" "$API/owners" | python -c "import sys,json;print(json.load(sys.stdin)[0]['owner']['id'])")
echo "ownerId=$OWNER"

echo "== 检查是否已有同名服务 =="
EXISTING=$(curl -sf -H "$AUTH" "$API/services?name=$SERVICE_NAME" | python -c "import sys,json;d=json.load(sys.stdin);print(d[0]['service']['id'] if d else '')")

if [ -n "$EXISTING" ]; then
  SVC_ID=$EXISTING
  echo "已存在服务 $SVC_ID，触发重新部署"
else
  echo "== 创建 Docker Web 服务 =="
  SVC_ID=$(curl -sf -X POST -H "$AUTH" -H "$CT" "$API/services" -d "{
    \"type\": \"web_service\",
    \"name\": \"$SERVICE_NAME\",
    \"ownerId\": \"$OWNER\",
    \"env\": \"docker\",
    \"repo\": \"$REPO\",
    \"branch\": \"$BRANCH\",
    \"plan\": \"free\",
    \"healthCheckPath\": \"/api/health\"
  }" | python -c "import sys,json;print(json.load(sys.stdin)['service']['id'])")
  echo "创建成功: $SVC_ID"
fi

echo "== 触发部署 =="
curl -sf -X POST -H "$AUTH" -H "$CT" "$API/services/$SVC_ID/deploys" -d '{}' > /dev/null || true

echo "== 等待服务上线（最长 10 分钟）=="
URL=$(curl -sf -H "$AUTH" "$API/services/$SVC_ID" | python -c "import sys,json;d=json.load(sys.stdin);print(d['service']['serviceDetails']['url'])")
echo "服务地址: $URL"

for i in $(seq 1 60); do
  sleep 10
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL/api/health" || true)
  if [ "$CODE" = "200" ]; then
    echo "部署成功！"
    echo "手机浏览器打开: $URL  → 添加到主屏幕即可安装 App"
    exit 0
  fi
  echo "  等待中 ($i/60, 当前状态码 $CODE)"
done
echo "超时：请登录 Render Dashboard 查看构建日志"
exit 1
