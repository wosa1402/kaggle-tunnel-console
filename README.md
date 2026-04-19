# Kaggle 隧道控制台

用 Web 控制面板启动多个 Kaggle 账号的笔记本（隧道暴露本地模型），一键推送批处理运行。

## 准备模板 ipynb

把你 Kaggle 上带隧道代码的笔记下载（或本地编辑），**把硬编码的 token 替换成 `{{TUNNEL_TOKEN}}`**，保存为 `data/template.ipynb`。

例：
```python
TUNNEL_TOKEN = "{{TUNNEL_TOKEN}}"
subprocess.run(['cloudflared', 'tunnel', 'run', '--token', TUNNEL_TOKEN])
```

## 本地开发

```bash
cp .env.example .env
# 编辑 .env，设置 ADMIN_PASSWORD 和 JWT_SECRET
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

访问 http://localhost:8000

## VPS 部署

```bash
# 在 VPS 上
git clone <your-repo> && cd kaggle-tunnel-console
cp .env.example .env
# 编辑 .env
docker compose up -d
```

建议前面挂 Caddy/Nginx 做 HTTPS。

## 使用流程

1. 登录（`.env` 里的 ADMIN_USERNAME/PASSWORD）
2. 点"添加账号"，填：别名、Kaggle 用户名、API Key、Kernel slug、隧道 token、固定 URL
3. 点卡片上"启动"，后端会：
   - 把 `data/template.ipynb` 中的 `{{TUNNEL_TOKEN}}` 替换为该账号的 token
   - 用该账号凭证调用 `kaggle kernels push`
   - Kaggle 服务器后台开始运行（关浏览器不会停）
4. 状态卡片每 15 秒自动刷新，显示运行时长

## 注意

- Kaggle 批处理最长 12 小时，到点自动结束，需要重新点"启动"
- 一个 slug 同一时间只能跑一个实例
- **API key 和隧道 token 使用 Fernet (AES-128) 加密后存入 SQLite**，主密钥在 `.env` 的 `ENCRYPTION_KEY`。务必：
  - 首次部署前生成：`python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`
  - 妥善备份 `.env`（丢了这把 key = 所有已存账号凭证解不开）
  - 不要改 key（换 key 需先导出→改 key→重新导入所有账号）
- **登录防爆破**：同 IP 10 分钟内失败 5 次将锁定 15 分钟（返回 429）。反向代理部署时需正确传递 `X-Forwarded-For`，否则限速会按代理 IP 生效
