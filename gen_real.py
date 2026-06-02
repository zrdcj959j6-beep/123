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
    {"url": "https://36kr.com/p/3834277983610753", "title": "黄仁勋宣布Rubin全面投产，4万名工程师参与构建，史上最强CPU同步亮相", "source": "36氪"},
    {"url": "https://www.ithome.com/0/958/480.htm", "title": "微软首个自研推理AI模型MAI-Thinking-1、新Copilot超级应用曝光", "source": "IT之家"},
    {"url": "https://www.ithome.com/0/958/727.htm", "title": "黄仁勋回应AI威胁论，称现在是软件公司的绝佳时代", "source": "IT之家"},
    {"url": "https://arstechnica.com/2026/06/", "title": "Ars Technica June 2026: AI costs, GitHub Copilot pricing, Meta AI chatbot hacked", "source": "Ars Technica"},
    {"url": "https://36kr.com/p/3834111984363401", "title": "VAST斩获近2亿美元A轮系列融资，同步推出世界模型", "source": "36氪"},
    {"url": "https://m.ithome.com/html/958103.htm", "title": "英伟达推出全球首款全开源全模态物理AI大模型Cosmos 3", "source": "IT之家"},
    {"url": "https://www.oreilly.com/radar/radar-trends-to-watch-june-2026/", "title": "Radar Trends to Watch: June 2026", "source": "O'Reilly"},
    {"url": "https://www.cnblogs.com/dqtx33/p/20255492", "title": "OpenAI终于下场做机器人，ChatGPT下一站是现实世界", "source": "博客园"},
    {"url": "https://www.36kr.com/p/3833957693515398", "title": "这届10后20后，已经不想跟真人聊天了？AI原住民时代来临", "source": "36氪"},
    {"url": "https://m.ithome.com/html/958109.htm", "title": "英伟达和台积电将AI引入晶圆厂，推动半导体设计与制造发展", "source": "IT之家"},
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
