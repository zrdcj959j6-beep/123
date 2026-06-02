# 🤖 AI 日报 - 自动更新 AI 新闻网站

每天自动抓取多个 RSS 源，通过 OpenAI API 生成中文摘要、标签、热度评分，在 GitHub Pages 上展示。

## ✨ 功能

- **热点速递**：多源 AI 新闻聚合，中文摘要，热度排序
- **AI 学习**：每日 AI 术语解释 + 最新 ArXiv 论文中文解读
- **自动更新**：Windows 定时任务每天自动运行 Python 脚本，推送到 Gitee
- **暗色模式**：现代风格单页，响应式布局

## 📁 文件结构

```
├── fetch_daily.py          # 吃瓜日常内容抓取
├── index.html             # 前端单页（暗色模式，3 Tab）
├── news.json              # 全量新闻（12条+）
├── hot_news.json          # 热点新闻，热度>=30
├── daily.json             # 吃瓜日常内容
├── learning.json          # AI 学习内容
├── requirements.txt       # Python 依赖
├── update_and_deploy.bat  # Windows 自动更新+部署脚本
└── 浏览器/                # Chrome 安装包（已忽略）
```

## 🚀 配置步骤

### 1. 创建 GitHub 仓库

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:你的用户名/你的仓库名.git
git push -u origin main
```

### 2. 设置 OpenAI API Key

在仓库的 **Settings → Secrets and variables → Actions** 中添加：

| Secret 名 | 值 |
|---|---|
| `OPENAI_API_KEY` | `sk-xxxxxxxxxxxxxxxx` |

### 3. 启用 GitHub Pages

在仓库的 **Settings → Pages** 中：

1. **Source** 选择 `GitHub Actions`
2. 保存即可

首次推送后，GitHub Actions 会自动部署。部署完成后，网站地址在 `https://你的用户名.github.io/仓库名/`。

### 4. 手动触发

在仓库的 **Actions** 标签页 → **Daily AI News Update** → **Run workflow** 可以手动触发一次更新。

## 🛠 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key
export OPENAI_API_KEY="sk-xxxxxxxx"

# 运行新闻抓取
python fetch_news.py

# 运行学习内容生成
python generate_learning.py

# 打开 index.html 查看效果（需要本地 HTTP 服务，因为用到了 fetch）
python -m http.server 8080
# 浏览器打开 http://localhost:8080
```

## 📡 RSS 源

| 来源 | URL | 权重 |
|---|---|---|
| HackerNews | hnrss.org/frontpage | 15 |
| TechCrunch | techcrunch.com AI 分类 | 25 |
| Reddit ML | reddit.com/r/MachineLearning | 15 |
| ArXiv CS.AI | arxiv.org AI 论文 | 20 |

可在 `fetch_news.py` 的 `RSS_FEEDS` 列表中增减。

## 🏷 热度评分规则

- 基础分 40
- 来源权威分（ArXiv 20, TechCrunch 25, HN/Reddit 15）
- 标题关键词加分（GPT, AGI, breakthrough, LLM 等，最高 +10）
- 多源报道加分（2 源 +10，3 源以上 +20）
- 新鲜度加分（6h 内 +10，12h 内 +5，24h 内 +2）

热度 ≥ 60 的进入 `hot_news.json`，在前端"热点速递"标签展示。

## 🔧 自定义

- **增加 RSS 源**：编辑 `fetch_news.py` 的 `RSS_FEEDS` 列表
- **调整关键词权重**：编辑 `TITLE_KEYWORD_BONUS` 字典
- **修改热度阈值**：修改 `HOT_THRESHOLD`（默认 60）
- **更换 AI 模型**：修改两脚本中的 `model="gpt-4o-mini"` 为其他模型

## 📄 License

MIT
