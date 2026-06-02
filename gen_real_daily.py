#!/usr/bin/env python3
"""吃瓜日常 — 真实URL + DeepSeek中文摘要"""
import json, os, sys, re
from datetime import datetime, timezone
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com")

# 真实文章（WebSearch 搜索结果，链接可直接打开）
REAL_DAILY = [
    {"url": "https://hypebeast.com/2026/4/ikea-x-chupa-chups-turn-swedish-meatball-lollipop-real",
     "title": "IKEA x Chupa Chups推出瑞典肉丸味棒棒糖，全球限量100万支",
     "category": "美食", "mood": "amaze"},
    {"url": "https://egw.news/gaming/news/35000/robloxs-catch-a-brainrot-might-be-the-internets-we-gMHPT-Wj0",
     "title": "Roblox用宝可梦方式收集网络梗生物，成2026最奇怪新游",
     "category": "游戏", "mood": "funny"},
    {"url": "https://thepeninsulaqatar.com/article/01/06/2026/chinese-relive-wonderful-youth-in-viral-sneak-eating-contest",
     "title": "北京商场上课偷吃零食大赛走红，数百成年人重温童年",
     "category": "生活", "mood": "nostalgia"},
    {"url": "https://feedback.minecraft.net/hc/en-us/community/posts/46276193109773-Squirrels-in-the-new-dappled-biome",
     "title": "Minecraft新斑驳生物群系或将加入松鼠：会爬树种树还扔雪球",
     "category": "游戏", "mood": "cute"},
    {"url": "https://arstechnica.com/gaming/2026/06/", "title": "Ars Technica: GitHub Copilot pricing backlash and AI gaming trends",
     "category": "科技生活", "mood": "hype"},
    {"url": "https://www.ithome.com/0/958/480.htm", "title": "微软首个自研推理AI模型曝光，Copilot将变身超级应用",
     "category": "科技生活", "mood": "amaze"},
    {"url": "https://36kr.com/p/3833957693515398", "title": "这届10后20后已经不想跟真人聊天了？AI原住民时代来临",
     "category": "科技生活", "mood": "funny"},
    {"url": "https://www.ithome.com/0/958/727.htm", "title": "黄仁勋回应AI威胁论：现在是软件公司的绝佳时代",
     "category": "奇闻", "mood": "hype"},
    {"url": "https://36kr.com/p/3834111984363401", "title": "VAST斩获近2亿美元融资，世界模型赛道持续火热",
     "category": "科技生活", "mood": "hype"},
    {"url": "https://m.ithome.com/html/958103.htm", "title": "英伟达全开源Cosmos 3物理AI大模型：让机器人看懂世界",
     "category": "科技生活", "mood": "amaze"},
]

def ask_deepseek(system, user, temp=0.6, max_tokens=3000):
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role":"system","content":system}, {"role":"user","content":user}],
        temperature=temp, max_tokens=max_tokens
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"): raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)

def generate():
    print("🍉 用真实链接生成吃瓜日常...")
    system = """你是轻松有趣的生活娱乐编辑。给每条资讯生成: 吸引人的中文标题(20-35字)、100-150字中文内容（生动有趣像聊天一样）、3个关键词标签、保留原有category和mood。
输出JSON: {"items":[{"title_cn":"...","summary_cn":"...","tags":["...","..."],"category":"原category","mood":"原mood"}]}"""

    titles = [f"{i+1}. [{n['category']}/{n['mood']}] {n['title']}" for i,n in enumerate(REAL_DAILY)]
    user = "请为以下真实趣闻生成中文内容:\n" + "\n".join(titles)

    try:
        data = ask_deepseek(system, user, temp=0.7, max_tokens=3000)
        items = data.get("items", [])
        now = datetime.now(timezone.utc).isoformat()

        for i, item in enumerate(items):
            item["id"] = f"d{i+1:03d}"
            if i < len(REAL_DAILY):
                item["link"] = REAL_DAILY[i]["url"]
                if "category" not in item: item["category"] = REAL_DAILY[i]["category"]
                if "mood" not in item: item["mood"] = REAL_DAILY[i]["mood"]
            item["published"] = now

        result = {"updated": now, "count": len(items), "items": items}
        with open("daily.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"  ✓ daily.json: {len(items)} 条真实链接")
        for i, item in enumerate(items):
            print(f"  [{i+1}] {item['title_cn'][:45]} → {item['link'][:55]}")
        return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print(f"🍉 吃瓜日常真实链接生成 — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)
    ok = generate()
    print(f"\n{'✅ 完成' if ok else '❌ 失败'}")
