#!/usr/bin/env python3
"""
🍉 吃瓜日常 — 多样化休闲内容抓取
- 抓取多个轻松 RSS 源（趣闻、游戏、美食、科技八卦等）
- 调用 OpenAI API 生成中文标题和趣味点评
- 输出到 daily.json
"""

import feedparser
import json
import os
import random
import sys
import urllib.request
import ssl
import time
from datetime import datetime, timezone
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────
DAILY_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily.json")
FEED_UA = "AIDailyBot/1.0 (News Aggregator; +https://github.com)"
FEED_TIMEOUT = 20
feedparser.USER_AGENT = FEED_UA

# 多样化 RSS 源
RSS_FEEDS = [
    # 趣味 / 奇闻
    {"url": "https://www.reddit.com/r/todayilearned/.rss", "name": "TodayILearned", "category": "冷知识"},
    {"url": "https://www.reddit.com/r/interestingasfuck/.rss", "name": "Interesting", "category": "奇闻"},
    {"url": "https://www.reddit.com/r/Damnthatsinteresting/.rss", "name": "DamnInteresting", "category": "奇闻"},
    # 科技八卦
    {"url": "https://www.reddit.com/r/gadgets/.rss", "name": "Gadgets", "category": "科技生活"},
    {"url": "https://www.reddit.com/r/technology/.rss", "name": "Technology", "category": "科技生活"},
    # 游戏
    {"url": "https://www.reddit.com/r/gaming/.rss", "name": "Gaming", "category": "游戏"},
    # 美食
    {"url": "https://www.reddit.com/r/food/.rss", "name": "Food", "category": "美食"},
    # 生活
    {"url": "https://www.reddit.com/r/LifeProTips/.rss", "name": "LifeTips", "category": "生活"},
    {"url": "https://www.reddit.com/r/mildlyinteresting/.rss", "name": "MildlyInteresting", "category": "趣图"},
]

# 备选：如果 RSS 全部不可用，使用这些趣味内容
FALLBACK_ITEMS = [
    {
        "title_cn": "考古学家在意大利发现2000年前的披萨壁画",
        "summary_cn": "在庞贝古城遗址中，考古学家发现了一幅保存完好的壁画，描绘了类似现代披萨的食物——扁平面饼上铺满水果和香料。虽然缺少番茄和马苏里拉（这两种食材当时还未传入欧洲），但这被认为是披萨最早的视觉记录之一。网友们纷纷表示：「原来意大利人对披萨的执着已经两千年了！」",
        "category": "美食", "mood": "amaze", "link": "https://example.com/pizza"
    },
    {
        "title_cn": "日本程序员用 ChatGPT 写了一本恋爱小说，意外登上畅销榜",
        "summary_cn": "一位不会谈恋爱的日本程序员用 ChatGPT 辅助写了一本恋爱小说《代码与心跳》，结果小说因为其「理工男式浪漫」意外走红，连续三周位列亚马逊日本恋爱小说榜 TOP10。作者本人在采访中说：「我只是把我希望发生在自己身上的故事写了出来而已…」读者评论：「这才是真正的科幻小说。」",
        "category": "科技生活", "mood": "funny", "link": "https://example.com/novel"
    },
    {
        "title_cn": "猫咪学会开智能门锁，主人装了三层防护才拦住",
        "summary_cn": "一位铲屎官在 Reddit 上分享了自家猫咪"越狱"的监控录像：这只聪明的橘猫通过观察主人操作，学会了用爪子触碰智能门锁的指纹区。虽然指纹不匹配无法开门，但它成功触发了警报系统。最终主人不得不加装了一个需要旋转把手才能解锁的物理锁。「这是我家猫智商最高的一次，也是我最破费的一次。」",
        "category": "趣图", "mood": "funny", "link": "https://example.com/cat"
    },
    {
        "title_cn": "睡眠专家揭示最佳午睡时长：26分钟",
        "summary_cn": "NASA 的一项睡眠研究意外走红社交网络。研究发现，26分钟是「咖啡因午觉」的黄金时长——喝完咖啡立刻睡26分钟，醒来时咖啡因刚好起效，补觉+提神双效合一。飞行员实验显示，这种方式能让下午的警觉度提升54%。网友：「原来我每天中午犯困26分钟后自然醒，是 NASA 认证的科学操作。」",
        "category": "冷知识", "mood": "useful", "link": "https://example.com/nap"
    },
    {
        "title_cn": "《GTA 6》最新预告片24小时播放量突破2亿",
        "summary_cn": "Rockstar 发布的《GTA 6》第二支预告片在24小时内播放量突破2亿次，打破了 YouTube 游戏类视频的历史记录。预告片展示了迈阿密风格的城市、复古跑车追逐战和网友戏称为「佛州男人模拟器」的各种荒诞场景。Reddit 网友已经开始逐帧分析，声称在背景中找到了《GTA 3》主角的彩蛋。",
        "category": "游戏", "mood": "hype", "link": "https://example.com/gta6"
    },
    {
        "title_cn": "瑞典公司推出「摸鱼模式」办公椅，自动调节到躺平角度",
        "summary_cn": "瑞典一家家具公司推出了一款智能办公椅，内置传感器检测用户坐姿，当检测到「摸鱼姿态」（单手托腮、身体倾斜、目光呆滞）超过5分钟，椅子自动调节到135°躺平模式并弹出小桌板。产品宣传语是「既然要摸鱼，不如躺平摸」。售价 899 美元，首批 5000 把在 3 小时内售罄。",
        "category": "科技生活", "mood": "funny", "link": "https://example.com/chair"
    },
    {
        "title_cn": "米其林大厨挑战用便利店食材做高级料理",
        "summary_cn": "YouTube 上一位米其林三星主厨发起了「便利店挑战」系列：只用 7-Eleven 的食材做出高级餐厅出品。最新一期用饭团、关东煮和薯片做出了分子料理风格的「日式怀石便当」，观看量超过 800 万。评论区：「看完觉得自己每天的便利店午餐都是在浪费生命。」",
        "category": "美食", "mood": "amaze", "link": "https://example.com/chef"
    },
    {
        "title_cn": "科学家证实：看可爱动物视频能降低工作压力 40%",
        "summary_cn": "英国利兹大学的一项随机对照研究表明，每天午休时观看 10 分钟可爱动物视频（如小猫、小狗、小熊猫等），唾液皮质醇水平平均降低 40%，下午工作效率提升 18%。研究还发现，观看熊猫打喷嚏的视频效果最佳。网友们：「终于有科学依据可以光明正大摸鱼了！」",
        "category": "冷知识", "mood": "useful", "link": "https://example.com/animal"
    },
    {
        "title_cn": "巨型橡皮鸭时隔十年重返香港维多利亚港",
        "summary_cn": "荷兰艺术家霍夫曼的巨型橡皮鸭在2013年首秀后，时隔十年终于重返香港维多利亚港。这次带来了「鸭子+鸭友」双鸭组合——两只18米高的橡皮鸭在维港漂浮巡游。网友们纷纷打卡：「十年了，我从大学生变成了打工人，鸭子还是那么大。」台湾网友：「我们的大黄鸭什么时候回来？」",
        "category": "奇闻", "mood": "nostalgia", "link": "https://example.com/duck"
    },
    {
        "title_cn": "日本推出「防社恐」透明厕所，有人走近自动变不透明",
        "summary_cn": "东京涩谷公园安装了由坂茂设计的透明公共厕所——平时完全透明，让人可以看清内部是否干净；一旦有人进入并锁门，玻璃会自动雾化变为不透明。如果30分钟内没有人开门，玻璃会重新变透明以防意外。网友：「设计很人性化，但社恐患者可能会担心雾化不够快。」",
        "category": "奇闻", "mood": "funny", "link": "https://example.com/toilet"
    },
    {
        "title_cn": "AI 生成了一张「完美披萨」的照片，结果引发地域战争",
        "summary_cn": "一张由 Midjourney 生成的「世界最完美披萨」图片在 Twitter 上爆红，结果因为披萨上出现了菠萝、意面、草莓等争议配料，引发了意大利网友的强烈抗议，以及美国网友的反击。评论区变成了各国饮食文化大混战。最终 Midjourney 官方被迫发了一条推文：「AI 没有味觉，来自全世界的食材它都一视同仁。」",
        "category": "美食", "mood": "funny", "link": "https://example.com/ai-pizza"
    },
    {
        "title_cn": "任天堂官宣 Switch 2 首发游戏阵容，玩家钱包瑟瑟发抖",
        "summary_cn": "任天堂在发布会上正式公开 Switch 2 首发护航游戏阵容，包括《塞尔达传说》新作、4K《马里奥赛车》、《宝可梦》开放世界新作等 12 款第一方作品。发布会后 #RIPWallet（钱包安息） 冲上 Twitter 热搜。玩家：「刚攒够钱买主机，现在告诉我还要准备游戏钱？」",
        "category": "游戏", "mood": "hype", "link": "https://example.com/switch2"
    },
    {
        "title_cn": "网红咖啡师用拉花还原世界名画",
        "summary_cn": "韩国首尔的一位咖啡师因其用奶泡拉花还原世界名画的视频走红网络。从梵高的《星空》到蒙克的《呐喊》，再到葛饰北斋的《神奈川冲浪里》，每杯作品的精细程度让人不忍心喝。制作一杯需要 15-20 分钟，售价约 30 美元。网友：「这不是咖啡，这是可以喝的艺术品。」",
        "category": "美食", "mood": "amaze", "link": "https://example.com/latte-art"
    },
    {
        "title_cn": "研究发现：人脑在洗澡时最容易产生创意灵感",
        "summary_cn": "哈佛大学创造力研究中心追踪了 500 位创意工作者，发现洗澡时产生灵感洞察的概率是工作时的 2.7 倍，仅次于「睡前半梦半醒状态」。研究解释：淋浴提供了适度的感官干扰（白噪音、温水触觉），恰好让默认模式网络活跃，但又不会完全占据注意力。网友：「难怪我每次洗澡都能想到绝妙的回怼，洗完就忘了。」",
        "category": "冷知识", "mood": "useful", "link": "https://example.com/shower"
    },
    {
        "title_cn": "2026 世界杯吉祥物「太空熊猫」正式亮相",
        "summary_cn": "2026 年美加墨世界杯官方吉祥物正式揭晓——一只穿着宇航服的熊猫，名字叫「AstroPanda」。设计理念融合了中国元素和太空探索主题，象征足球连接全世界。社交媒体反响两极分化：有人觉得可爱，有人觉得「熊猫和世界杯有什么关系？」中国网友：「我们派出熊猫做文化输出，有什么问题吗？」",
        "category": "奇闻", "mood": "hype", "link": "https://example.com/worldcup"
    },
]

# 心情分类
MOOD_MAP = {
    "funny": "😂 笑死", "amaze": "🤯 震撼", "useful": "💡 实用",
    "hype": "🔥 热门", "nostalgia": "🥹 回忆杀", "cute": "🥰 可爱",
}

# OpenAI 客户端
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com")


# ── 工具函数 ──────────────────────────────────────────

def _fetch_rss(url, timeout=FEED_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": FEED_UA})
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
        return feedparser.parse(raw)
    except Exception as e:
        result = feedparser.parse("")
        result.bozo = True
        result.bozo_exception = e
        return result


def fetch_feed(feed_config):
    entries = []
    try:
        resp = _fetch_rss(feed_config["url"])
        if resp.bozo:
            print(f"  ⚠ {feed_config['name']} 问题: {resp.bozo_exception}", file=sys.stderr)
        for entry in resp.entries[:8]:  # 每个源最多取 8 条
            title = entry.get("title", "").strip()
            if not title:
                continue
            # 清理 Reddit 标题前缀
            title = title.replace("[r/todayilearned] ", "").replace("[TIL] ", "")
            entries.append({
                "title": title[:200],
                "link": entry.get("link", ""),
                "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                "summary_original": entry.get("summary", entry.get("description", ""))[:500],
                "category": feed_config["category"],
                "source_name": feed_config["name"],
            })
        print(f"  ✓ {feed_config['name']}: {len(entries)} 条")
    except Exception as e:
        print(f"  ✗ {feed_config['name']}: {e}", file=sys.stderr)
    return entries


def call_openai_for_daily(item):
    """调用 OpenAI 生成中文标题和趣味点评"""
    system_prompt = """你是一个轻松有趣的日常资讯编辑，风格幽默风趣，擅长"讲人话"。对用户提供的资讯：
1. 生成一个吸引人的中文标题（口语化，可以在20-35字之间，要有趣不枯燥）
2. 生成一段中文点评或介绍（100-180字，要求生动有趣、有笑点或知识点，像朋友聊天一样自然）
3. 判断心情标签：funny（搞笑）/ amaze（震撼）/ useful（实用）/ cute（可爱）/ hype（热门）/ nostalgia（怀旧）
4. 提炼1-3个关键词标签

严格输出 JSON：
{"title_cn": "...", "summary_cn": "...", "mood": "funny", "tags": ["...", "..."]}"""

    user_prompt = f"标题: {item['title']}\n分类: {item.get('category', '')}\n内容摘要: {item.get('summary_original', '（无）')[:400]}"

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content.strip())
        return {
            "title_cn": data.get("title_cn", item["title"]),
            "summary_cn": data.get("summary_cn", "（暂无详细介绍）"),
            "mood": data.get("mood", "funny"),
            "tags": data.get("tags", []),
        }
    except Exception as e:
        print(f"  OpenAI 调用失败: {e}", file=sys.stderr)
        moods = ["funny", "amaze", "useful", "cute"]
        return {
            "title_cn": item["title"],
            "summary_cn": "（AI 点评暂时不可用，请稍后刷新）",
            "mood": random.choice(moods),
            "tags": [],
        }


# ── 主逻辑 ────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"🍉 吃瓜日常 — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. 抓取所有 RSS
    print("\n📡 抓取多样化内容...")
    all_entries = []
    for feed_config in RSS_FEEDS:
        entries = fetch_feed(feed_config)
        all_entries.extend(entries)
        time.sleep(0.3)

    print(f"\n📊 共抓取 {len(all_entries)} 条原始条目")

    # 2. 如果抓取太少，用备选内容补足
    use_fallback = len(all_entries) < 5
    if use_fallback:
        print(f"⚠ RSS 抓取不足，使用本地备选内容补足")
        # 随机选12条备选内容
        items_to_process = random.sample(
            FALLBACK_ITEMS, min(12, len(FALLBACK_ITEMS))
        )
        # 转换格式
        processed = []
        for item in items_to_process:
            processed.append({
                "id": f"fb_{abs(hash(item['title_cn'])) % 100000:05d}",
                "title_cn": item["title_cn"],
                "summary_cn": item["summary_cn"],
                "category": item["category"],
                "mood": item.get("mood", "funny"),
                "tags": [item["category"]],
                "link": item.get("link", ""),
                "published": datetime.now(timezone.utc).isoformat(),
            })
        print(f"使用 {len(processed)} 条备选内容")
    else:
        # 3. 去重（标题相似度简单去重）
        seen_titles = set()
        unique_entries = []
        for entry in all_entries:
            key = entry["title"].lower()[:60]
            if key not in seen_titles:
                seen_titles.add(key)
                unique_entries.append(entry)

        # 每个分类最多保留 5 条，确保多样性
        from collections import defaultdict
        category_count = defaultdict(int)
        diverse_entries = []
        for entry in unique_entries:
            cat = entry["category"]
            if category_count[cat] < 5:
                category_count[cat] += 1
                diverse_entries.append(entry)

        # 随机选取最多 20 条
        if len(diverse_entries) > 20:
            diverse_entries = random.sample(diverse_entries, 20)

        print(f"去重+多样化筛选后: {len(diverse_entries)} 条")
        for cat, count in sorted(category_count.items()):
            print(f"  {cat}: {count} 条")

        # 4. AI 处理
        print("\n🤖 AI 生成中文内容...")
        processed = []
        for i, item in enumerate(diverse_entries):
            ai_result = call_openai_for_daily(item)
            processed.append({
                "id": f"daily_{abs(hash(item['title'])) % 100000:05d}",
                "title_cn": ai_result["title_cn"],
                "summary_cn": ai_result["summary_cn"],
                "category": item["category"],
                "mood": ai_result.get("mood", "funny"),
                "tags": ai_result.get("tags", []),
                "link": item["link"],
                "published": item["published"],
            })
            print(f"  [{i+1}/{len(diverse_entries)}] {ai_result['title_cn'][:50]}...")
            time.sleep(0.3)

    # 5. 混合打乱，让不同分类交错出现
    random.shuffle(processed)

    # 6. 保存
    now_iso = datetime.now(timezone.utc).isoformat()
    output = {
        "updated": now_iso,
        "count": len(processed),
        "items": processed,
    }

    with open(DAILY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ daily.json 已生成: {len(processed)} 条")
    print(f"📁 路径: {DAILY_JSON_PATH}")


if __name__ == "__main__":
    main()
