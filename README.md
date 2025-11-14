# Reddit Painpoint Planner (MVP)

- 输入 subreddit 和 keyword，检索高赞帖子。
- 选择帖子，点击“生成执行计划”，调用 Mistral API 输出固定 Markdown 结构。
- 展示 Markdown 与渲染预览，支持复制与下载 PDF。
- 每日（UTC）AI Token 配额 100,000，超出则提示次日再来。

## 开发与运行

1. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填写 Mistral API Key
```

3. 运行

```bash
export FLASK_APP=app.py
flask run --port 5000
# 或 python app.py
```

访问 http://localhost:5000

## 部署与仓库

- 初始化新的 Git 仓库并推送到 GitHub 新仓库。
- 在 Cloudflare Pages 连接该仓库（或使用其他部署方式）。

## 备注

- Reddit 仅使用公开 JSON 接口，设置了 User-Agent。
- Token 统计为粗略估算（字符/4）。如需严谨计量，可接入官方计费/usage接口或 tokenizer。
