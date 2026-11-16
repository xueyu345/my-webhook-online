# My Webhook Online

平板友好的 HTML 前端 + FastAPI 后端 + PostgreSQL。支持多账号隔离、Endpoint 管理、真实 HTTP Webhook 接收和请求日志。

## 重要边界
- 这是可运行的基础版本，不是 ngrok 的完整替代品。
- Webhook 接收地址为 `/webhook/{token}`。
- 当前版本没有原生 TCP/HTTP 隧道 Agent、邮件验证、密码找回、管理员控制台、请求转发和速率限制。
- 上线公网前必须增加 HTTPS 反向代理、速率限制、请求体大小限制、日志保留策略、备份和监控。不要直接暴露未经加固的实例。

## 本地开发（SQLite）
需要 Python 3.11+。
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```
设置环境变量：
```bash
# macOS/Linux
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
# Windows PowerShell
$env:JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
```
运行：
```bash
uvicorn app.main:app --reload
```
打开 http://127.0.0.1:8000

## Docker + PostgreSQL
```bash
cp .env.example .env
```
编辑 `.env`，将 JWT_SECRET 和 POSTGRES_PASSWORD 替换为长随机值，并确保 DATABASE_URL 中的密码与 POSTGRES_PASSWORD 完全一致。
```bash
docker compose up -d --build
```
打开 `http://服务器IP:8000`。生产环境请放在 Caddy/Nginx 后面启用 HTTPS，不要直接把 8000 端口作为公网生产入口。

## 测试 Webhook
注册登录后创建 Endpoint，复制页面显示的 `/webhook/{token}` 地址：
```bash
curl -X POST 'http://127.0.0.1:8000/webhook/替换为token' \
  -H 'Content-Type: application/json' \
  -d '{"event":"demo","message":"hello"}'
```
请求会进入对应账号的日志。响应内容和状态码可以在界面中调整。

## API
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/me`
- `GET/POST /api/endpoints`
- `PATCH/DELETE /api/endpoints/{id}`
- `GET/DELETE /api/logs`
- `GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD /webhook/{token}`
- `GET /health`

## 平板开发
可用任意支持 ZIP 解压和文本编辑的平板代码编辑器修改 `app/static/index.html`；后端部署在 VPS 或云主机，平板浏览器访问部署地址即可。
