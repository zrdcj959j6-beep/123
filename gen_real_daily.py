#!/usr/bin/env python3
"""吃瓜日常 — 真实URL + DeepSeek中文摘要"""
import json, os, sys, re
from datetime import datetime, timezone
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com")

# 真实文章（WebSearch 搜索结果，链接可直接打开）
REAL_DAILY = [
    {"url": "https://m.toutiao.com/w/1866852607375372/",
     "title": "河北聪明小猪偷吃饼干后疯狂摇头否认，还自制抽屉楼梯爬上桌",
     "category": "奇闻", "mood": "funny"},
    {"url": "https://www.sanqin.com/2026-06/01/content_11616253.html",
     "title": "2026年6月6日周六\"四6同框\"上热搜，网友打卡沾喜气",
     "category": "奇闻", "mood": "hype"},
    {"url": "https://www.sohu.com/a/1030374328_120349075",
     "title": "全网群嘲的\"猪食火锅\"事件：石槽装火锅、中药奶茶等奇葩餐饮翻车",
     "category": "美食", "mood": "funny"},
    {"url": "https://hypebeast.com/2026/4/ikea-x-chupa-chups-turn-swedish-meatball-lollipop-real",
     "title": "IKEA x Chupa Chups推出瑞典肉丸味棒棒糖，全球限量100万支",
     "category": "美食", "mood": "amaze"},
    {"url": "https://egw.news/gaming/news/35000/robloxs-catch-a-brainrot-might-be-the-internets-we-gMHPT-Wj0",
     "title": "Roblox \"Catch a Brainrot\"：用宝可梦方式收集网络梗生物，成2026最奇怪新游",
     "category": "游戏", "mood": "funny"},
    {"url": "https://thepeninsulaqatar.com/article/01/06/2026/chinese-relive-wonderful-youth-in-viral-sneak-eating-contest",
     "title": "北京商场\"上课偷吃零食大赛\"走红，数百成年人重温童年",
     "category": "生活", "mood": "nostalgia"},
    {"url": "https://www.sohu.com/a/1030728959_121384220",
     "title": "37岁男子遭遇\"崩老头\"，花近200元请陪聊只拿到5张自拍和2条语音",
     "category": "趣图", "mood": "funny"},
    {"url": "https://3g.china.com/act/news/10000169/20260602/49526785.html",
     "title": "岳云鹏儿童节\"灵珠\"空降上海：上次过儿童节是30年前",
     "category": "奇闻", "mood": "funny"},
    {"url": "https://www.360kuai.com/90bc4bc0d2942c354",
     "title": "6月6日周六不上班！这样过\"最6星期六\"一年都顺风顺水",
     "category": "生活", "mood": "useful"},
    {"url": "https://feedback.minecraft.net/hc/en-us/community/posts/46276193109773-Squirrels-in-the-new-dappled-biome",
     "title": "Minecraft新\"斑驳\"生物群系或将加入松鼠：会爬树种树还扔雪球挑衅玩家",
     "category": "游戏", "mood": "cute"},
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
