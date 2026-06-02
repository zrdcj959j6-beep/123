#!/usr/bin/env python3
"""
真实新闻生成器 — 使用真实URL + DeepSeek翻译摘要
来源: WebSearch 搜索结果，链接真实可点击
"""

import json, os, sys
from datetime import datetime, timezone
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com")

# ── 真实新闻源（WebSearch 搜索结果，链接真实可打开）──
REAL_NEWS = [
    {"url": "https://www.jiqizhixin.com/articles/2026-06-02-6", "title": "图灵奖得主Sutton新作：AI的下一步，是走向「生成认知」", "source": "机器之心"},
    {"url": "https://www.jiqizhixin.com/articles/2026-06-02-10", "title": "英伟达一通发布，物理AI全都智能体化了", "source": "机器之心"},
    {"url": "https://techorange.com/2026/06/01/ai-agent-nvidia-computex-gtc-taipei-keynote/", "title": "黄仁勋宣布「有用的AI已经到来」：从AI工厂到实体AI，全面押注代理式AI", "source": "TechOrange"},
    {"url": "https://www.163.com/dy/article/KUDNAU9D0511FQO9.html", "title": "曝豆包将正式付费；xAI招募中文AI导师训练Grok；OpenAI现场演示无APP手机", "source": "网易/极客头条"},
    {"url": "https://www.chinaz.com/ainews/28556.shtml", "title": "颠覆传统交互！OpenAI现场演示无App手机，所有界面全靠AI实时生成", "source": "站长之家"},
    {"url": "https://www.aibase.com/zh/news/28495", "title": "狂砸750亿欧元！软银欧洲史上最大AI投资落地，联手OpenAI在法建立超级算力中心", "source": "AIbase"},
    {"url": "https://www.oreilly.com/radar/radar-trends-to-watch-june-2026/", "title": "Radar Trends to Watch: June 2026 — O'Reilly", "source": "O'Reilly"},
    {"url": "https://www.cnblogs.com/dqtx33/p/20255492", "title": "OpenAI终于下场做机器人，ChatGPT的下一站不是聊天，而是现实世界", "source": "博客园"},
    {"url": "https://blockchain.news/ainews/nvidia-rtx-spark-powers-windows-ai-breakthrough", "title": "NVIDIA RTX Spark Powers Windows AI Breakthrough", "source": "Blockchain News"},
    {"url": "https://www.theneuron.ai/explainer-articles/everything-that-happened-in-ai-today-monday-june-1-2026/", "title": "Everything That Happened in AI Today — Monday, June 1, 2026", "source": "The Neuron"},
]

def ask_deepseek(system, user, temp=0.5, max_tokens=800):
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"system","content":system}, {"role":"user","content":user}],
        temperature=temp, max_tokens=max_tokens
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"): raw = raw.split("\n",1)[-1]; raw = raw[:-3] if raw.endswith("```") else raw; raw = raw.strip()
    return json.loads(raw)

def generate_real_news():
    print("📰 用真实链接生成 AI 新闻...")
    system = """你是AI新闻编辑。给每条英文/中文新闻生成: 中文标题(20-30字)、中文摘要(100-150字)、3-5个标签、热度评分(50-95)。
输出JSON: {"items":[{"title_cn":"...","summary_cn":"...","tags":["...","..."],"hot_score":80}]}"""

    titles = [f"{i+1}. [{n['source']}] {n['title']}" for i,n in enumerate(REAL_NEWS)]
    user = "请为以下真实新闻生成中文内容:\n" + "\n".join(titles) + "\n\n注意：热度评分要合理分配，前3条90+，中间70-85，后面50-70。"

    try:
        data = ask_deepseek(system, user, temp=0.5, max_tokens=3000)
        items = data.get("items", [])
        now = datetime.now(timezone.utc).isoformat()

        for i, item in enumerate(items):
            item["id"] = f"r{i+1:03d}"
            item["title"] = REAL_NEWS[i]["title"]
            item["link"] = REAL_NEWS[i]["url"]
            item["sources"] = [REAL_NEWS[i]["source"]]
            item["published"] = now
            item["authority_weight"] = 20
            if "hot_score" not in item: item["hot_score"] = 60

        result = {"updated": now, "count": len(items), "news": items}
        hot = [i for i in items if i.get("hot_score", 0) >= 30]
        hot_result = {"updated": now, "count": len(hot), "news": hot}

        with open(os.path.join(SCRIPT_DIR, "news.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        with open(os.path.join(SCRIPT_DIR, "hot_news.json"), "w", encoding="utf-8") as f:
            json.dump(hot_result, f, ensure_ascii=False, indent=2)

        print(f"  ✓ news.json: {len(items)} 条真实链接 | hot_news.json: {len(hot)} 条")
        for i, item in enumerate(items):
            print(f"  [{i+1}] {item['title_cn'][:50]} → {item['link'][:60]}")
        return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print(f"🔗 真实新闻生成 — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)
    ok = generate_real_news()
    print(f"\n{'✅ 完成' if ok else '❌ 失败'}")
