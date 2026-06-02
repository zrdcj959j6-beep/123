#!/usr/bin/env python3
"""
AI 新闻抓取脚本
- 抓取多个 RSS 源
- 调用 OpenAI API 做中文摘要、打标签、热度评分
- 去重后生成 news.json（全量）和 hot_news.json（热度>=60）
"""

import feedparser
import json
import os
import re
import hashlib
import time
import sys
import urllib.request
import ssl
from datetime import datetime, timezone
from difflib import SequenceMatcher
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────

# 自定义 User-Agent，避免被 Reddit 等站点拦截
FEED_UA = "AIDailyBot/1.0 (News Aggregator; +https://github.com)"
FEED_TIMEOUT = 20  # RSS 抓取超时（秒）

# 设置 feedparser 全局 UA（兜底）
feedparser.USER_AGENT = FEED_UA

RSS_FEEDS = [
    {
        "url": "https://hnrss.org/frontpage",
        "name": "HackerNews",
        "authority_weight": 15,
    },
    {
        "url": "https://rss.techcrunch.com/category/artificial-intelligence",
        "name": "TechCrunch",
        "authority_weight": 25,
    },
    {
        "url": "https://www.reddit.com/r/MachineLearning/.rss",
        "name": "Reddit",
        "authority_weight": 15,
    },
    {
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "name": "ArXiv",
        "authority_weight": 20,
    },
]

# 标题关键词加分（不区分大小写）
TITLE_KEYWORD_BONUS = {
    "gpt": 10, "agi": 10, "artificial general intelligence": 10,
    "breakthrough": 8, "revolutionary": 8, "sota": 8,
    "openai": 8, "deepmind": 8, "anthropic": 8,
    "google": 7, "meta": 6, "microsoft": 6, "tesla": 5,
    "llm": 8, "large language model": 8, "transformer": 7,
    "diffusion": 7, "multimodal": 7, "agent": 6,
    "open source": 6, "launch": 5, "release": 5,
    "benchmark": 5, "surpass": 6, "beats": 6,
    "robot": 6, "humanoid": 6, "autonomous": 5,
    "chip": 6, "gpu": 6, "nvidia": 6,
    "safety": 5, "alignment": 5, "regulation": 5,
}

# 多源相同事件加分
MULTI_SOURCE_BONUS = 20

# 新闻文件路径
NEWS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news.json")
HOT_NEWS_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hot_news.json")
HOT_THRESHOLD = 30

# OpenAI 客户端
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com")

# ── 工具函数 ──────────────────────────────────────────

def _fetch_rss(url, timeout=FEED_TIMEOUT):
    """带 UA 和超时的 RSS 抓取，防止被拦截或卡死"""
    req = urllib.request.Request(url, headers={"User-Agent": FEED_UA})
    try:
        # 允许 TLS 1.2+，兼容各 RSS 源
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
        return feedparser.parse(raw)
    except Exception as e:
        # 网络错误时返回空结果，不中断整个流程
        result = feedparser.parse("")  # 构造空结果
        result.bozo = True
        result.bozo_exception = e
        return result


def fetch_feed(feed_config):
    """抓取单个 RSS 源，返回条目列表"""
    entries = []
    try:
        resp = _fetch_rss(feed_config["url"])
        if resp.bozo:
            print(f"  ⚠ {feed_config['name']} 网络/解析问题: {resp.bozo_exception}", file=sys.stderr)
        for entry in resp.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
            else:
                published = datetime.now(timezone.utc).isoformat()

            entries.append({
                "title": entry.get("title", "No Title").strip(),
                "link": entry.get("link", "").strip(),
                "published": published,
                "source_name": feed_config["name"],
                "authority_weight": feed_config["authority_weight"],
                "summary_original": entry.get("summary", entry.get("description", "")),
            })
        print(f"  ✓ {feed_config['name']}: {len(entries)} 条")
    except Exception as e:
        print(f"  ✗ {feed_config['name']}: {e}", file=sys.stderr)
    return entries


def title_similarity(t1, t2):
    """计算两个标题的相似度 (0~1)"""
    t1 = re.sub(r"[^a-zA-Z0-9一-鿿]", "", t1.lower())
    t2 = re.sub(r"[^a-zA-Z0-9一-鿿]", "", t2.lower())
    if not t1 or not t2:
        return 0
    return SequenceMatcher(None, t1, t2).ratio()


def deduplicate(entries, threshold=0.65):
    """
    基于标题相似度去重，保留 authority_weight 最高的来源。
    同时记录同一事件被哪些来源报道过。
    """
    clusters = []  # list of {"entries": [...], "merged": {...}}

    for entry in entries:
        matched = False
        for cluster in clusters:
            for member in cluster["entries"]:
                if title_similarity(entry["title"], member["title"]) >= threshold:
                    cluster["entries"].append(entry)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            clusters.append({"entries": [entry]})

    merged_news = []
    for cluster in clusters:
        # 选 authority_weight 最高者作为主条目
        best = max(cluster["entries"], key=lambda e: e["authority_weight"])
        sources = list(set(e["source_name"] for e in cluster["entries"]))
        merged = {
            "title": best["title"],
            "link": best["link"],
            "published": min(e["published"] for e in cluster["entries"]),
            "sources": sources,
            "authority_weight": max(e["authority_weight"] for e in cluster["entries"]),
            "multi_source_count": len(sources),
            "summary_original": best["summary_original"],
        }
        merged_news.append(merged)

    return merged_news


def compute_id(news):
    """为新闻生成唯一 ID"""
    raw = f"{news['title']}|{news['link']}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def compute_hot_score(news):
    """计算热度评分"""
    score = 40  # base

    # 来源权威分
    score += news.get("authority_weight", 10)

    # 多源加分
    if news.get("multi_source_count", 1) >= 3:
        score += MULTI_SOURCE_BONUS
    elif news.get("multi_source_count", 1) >= 2:
        score += MULTI_SOURCE_BONUS // 2

    # 标题关键词加分（只加一次，取最高匹配）
    title_lower = news["title"].lower()
    max_kw = 0
    for kw, bonus in TITLE_KEYWORD_BONUS.items():
        if kw in title_lower:
            max_kw = max(max_kw, bonus)
    score += max_kw

    # 新鲜度加分（发布时间越近分越高）
    try:
        pub = datetime.fromisoformat(news["published"].replace("Z", "+00:00"))
        hours_ago = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        if hours_ago < 6:
            score += 10
        elif hours_ago < 12:
            score += 5
        elif hours_ago < 24:
            score += 2
    except Exception:
        pass

    return min(score, 100)


def call_openai_for_news(news_item):
    """调用 OpenAI 生成中文摘要、标签"""
    system_prompt = """你是一个 AI 新闻编辑。对用户提供的英文科技新闻，请完成：
1. 中文标题（简洁有力，不超过30字）
2. 中文摘要（100-150字，讲清核心内容）
3. 标签（3-5个，中英文皆可，用英文逗号分隔）

严格输出 JSON，格式如下：
{"title_cn": "...", "summary_cn": "...", "tags": ["...", "..."]}"""

    user_prompt = f"标题: {news_item['title']}\n\n原始摘要: {news_item.get('summary_original', '（无）')[:500]}"

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        return {
            "title_cn": data.get("title_cn", news_item["title"]),
            "summary_cn": data.get("summary_cn", ""),
            "tags": data.get("tags", []),
        }
    except Exception as e:
        print(f"  OpenAI 调用失败: {e}", file=sys.stderr)
        return {
            "title_cn": news_item["title"],
            "summary_cn": "（摘要生成失败）",
            "tags": [],
        }


def load_existing_news():
    """加载已有的 news.json，用于复用已处理条目"""
    if os.path.exists(NEWS_JSON_PATH):
        try:
            with open(NEWS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"news": []}


def save_json(data, path):
    """保存 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 主逻辑 ────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"AI 新闻抓取开始 — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 1. 抓取所有 RSS
    print("\n📡 抓取 RSS 源...")
    all_entries = []
    for feed_config in RSS_FEEDS:
        entries = fetch_feed(feed_config)
        all_entries.extend(entries)
        time.sleep(0.5)  # 礼貌间隔

    print(f"\n📊 共抓取 {len(all_entries)} 条原始条目")

    if not all_entries:
        print("❌ 没有抓取到任何新闻，退出")
        return

    # 2. 去重
    print("\n🔍 去重中...")
    merged = deduplicate(all_entries)
    print(f"去重后剩余 {len(merged)} 条")

    # 3. 加载已有数据，建立 URL -> 已有处理结果 的映射
    existing_map = {}
    existing_news = load_existing_news()
    for old in existing_news.get("news", []):
        if old.get("link"):
            existing_map[old["link"]] = old

    # 4. 处理每条新闻（OpenAI 调用仅对新增条目）
    print("\n🤖 AI 处理中...")
    processed = []
    new_count = 0
    for i, item in enumerate(merged):
        news_id = compute_id(item)
        item["id"] = news_id

        # 复用已有翻译
        if item["link"] in existing_map and existing_map[item["link"]].get("title_cn"):
            cached = existing_map[item["link"]]
            item["title_cn"] = cached["title_cn"]
            item["summary_cn"] = cached["summary_cn"]
            item["tags"] = cached["tags"]
        else:
            ai_result = call_openai_for_news(item)
            item["title_cn"] = ai_result["title_cn"]
            item["summary_cn"] = ai_result["summary_cn"]
            item["tags"] = ai_result["tags"]
            new_count += 1
            time.sleep(0.3)  # API 限速

        # 计算热度
        item["hot_score"] = compute_hot_score(item)
        processed.append(item)
        print(f"  [{i+1}/{len(merged)}] {item['title'][:60]}... → 热度 {item['hot_score']}")

    print(f"\n新增 AI 处理: {new_count} 条，复用缓存: {len(merged) - new_count} 条")

    # 5. 按热度降序排列
    processed.sort(key=lambda x: x["hot_score"], reverse=True)

    # 6. 构建输出
    now_iso = datetime.now(timezone.utc).isoformat()
    output_fields = [
        "id", "title", "title_cn", "summary_cn", "tags",
        "hot_score", "link", "published", "sources", "authority_weight",
    ]

    all_news_data = {
        "updated": now_iso,
        "count": len(processed),
        "news": [{k: item[k] for k in output_fields if k in item} for item in processed],
    }

    hot_items = [item for item in processed if item["hot_score"] >= HOT_THRESHOLD]
    hot_news_data = {
        "updated": now_iso,
        "count": len(hot_items),
        "news": [{k: item[k] for k in output_fields if k in item} for item in hot_items],
    }

    # 7. 保存
    save_json(all_news_data, NEWS_JSON_PATH)
    save_json(hot_news_data, HOT_NEWS_JSON_PATH)

    print(f"\n✅ 完成！news.json: {len(processed)} 条 | hot_news.json: {len(hot_items)} 条")
    print(f"📁 输出路径: {os.path.dirname(NEWS_JSON_PATH)}")


if __name__ == "__main__":
    main()
