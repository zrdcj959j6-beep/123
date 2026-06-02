#!/usr/bin/env python3
"""
AI 日报 — DeepSeek 直接生成版
无需 RSS，DeepSeek 直接生成最新 AI 新闻 + 术语 + 论文解读 + 吃瓜日常
一键生成所有 JSON 文件
"""

import json
import os
from datetime import datetime, timezone
from openai import OpenAI

# ── 配置 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://api.deepseek.com"
)

def ask_deepseek(system_prompt, user_prompt, temp=0.5, max_tokens=800):
    """调用 DeepSeek API"""
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temp,
        max_tokens=max_tokens,
    )
    raw = resp.choices[0].message.content.strip()
    # 清理 markdown 包裹
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)

def generate_news():
    """生成 10 条 AI 新闻"""
    print("📰 生成 AI 新闻...")
    system = """你是 AI 日报主编。请生成 10 条 2026年6月初最新的 AI 科技新闻。
每条必须是独立、可信、英文原标题加中文翻译的新闻。
严格控制输出为以下 JSON 格式，不要任何额外文字。每条必须包含link字段：
{"news": [{"title": "English Title", "title_cn": "中文标题(20-30字)", "summary_cn": "中文摘要(100-150字)", "tags": ["标签1","标签2","标签3"], "hot_score": 50-95的数字, "sources": ["来源A","来源B"], "link": "https://techcrunch.com/2026/06/02/example-slug/"} , ...]}"""

    user = """请生成10条2026年6月初的最新AI新闻。要求：
1. 覆盖多个领域：大模型发布、AI芯片、AI安全监管、开源模型、机器人、AI融资、学术研究、AI应用
2. 热度分数分配合理：头部1-2条90+，中部3-5条70-85，尾部45-65
3. 每条source至少一个（如TechCrunch/ArXiv/VentureBeat/The Verge/Wired等）
4. 标题要有真实感，不要编造明显不存在的事件
5. 用中文生成title_cn和summary_cn
6. 极其重要：每条必须生成一个真实的link，指向假想的来源文章URL。URL必须指向真实存在的域名（如techcrunch.com、theverge.com、arstechnica.com、venturebeat.com、wired.com等），路径用news-title-slug格式，即使文章是虚构的，URL格式必须正确"""

    try:
        data = ask_deepseek(system, user, temp=0.6, max_tokens=3000)
        items = data.get("news", [])
        now = datetime.now(timezone.utc).isoformat()
        for i, item in enumerate(items):
            item["id"] = f"n{i+1:03d}"
            if "published" not in item:
                item["published"] = now
            if "authority_weight" not in item:
                item["authority_weight"] = 20
            if not item.get("link"):
                import re
                slug = re.sub(r'[^a-zA-Z0-9]+', '-', item.get("title", "news"))[:80].strip('-').lower()
                item["link"] = "https://techcrunch.com/2026/06/02/" + slug + "/"
        result = {"updated": now, "count": len(items), "news": items}
        hot = [i for i in items if i.get("hot_score", 0) >= 30]
        hot_result = {"updated": now, "count": len(hot), "news": hot}

        with open(os.path.join(SCRIPT_DIR, "news.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        with open(os.path.join(SCRIPT_DIR, "hot_news.json"), "w", encoding="utf-8") as f:
            json.dump(hot_result, f, ensure_ascii=False, indent=2)

        print(f"  ✓ news.json: {len(items)} 条 | hot_news.json: {len(hot)} 条")
        return True
    except Exception as e:
        print(f"  ✗ 新闻生成失败: {e}")
        return False

def generate_learning():
    """生成 AI 术语 + 论文解读"""
    print("📚 生成 AI 学习内容...")

    # 术语
    term_sys = """你是AI教育者。选一个2026年热门的AI术语（要有深度，别选'机器学习'这种基础词汇），用通俗中文解释。
输出JSON: {"word": "术语名称(中英文)", "explanation_cn": "150-250字中文解释"}"""

    term_user = "请选一个2026年AI领域有深度的热门术语来解释。"

    # 论文
    paper_sys = """你是AI论文解读专家。虚构一篇2026年6月发表的真实风格的AI论文，做中文解读。
输出JSON: {"title": "English Paper Title", "title_cn": "论文中文标题", "interpretation_cn": "300-500字中文解读(包含:问题背景、核心方法、实验效果、实际意义)", "authors": "作者名 et al. (机构)", "arxiv_id": "2506.xxxxx"}"""

    paper_user = "请生成一篇2026年6月的AI领域论文解读，领域可以是LLM/Agent/RAG/MoE/Multimodal等。"

    now = datetime.now(timezone.utc).isoformat()
    result = {"updated": now}

    try:
        term = ask_deepseek(term_sys, term_user, temp=0.8, max_tokens=500)
        result["term"] = term
        print(f"  ✓ 术语: {term.get('word', '?')}")
    except Exception as e:
        print(f"  ✗ 术语失败: {e}")
        result["term"] = {"word": "Mixture of Experts (MoE)", "explanation_cn": "MoE将网络分成多个专家子网络，每次只激活一部分，大幅降低推理成本。"}

    try:
        paper = ask_deepseek(paper_sys, paper_user, temp=0.6, max_tokens=1000)
        paper["link"] = f"https://arxiv.org/abs/{paper.get('arxiv_id', '2506.00001')}"
        paper["published"] = now
        result["paper"] = paper
        print(f"  ✓ 论文: {paper.get('title_cn', '?')}")
    except Exception as e:
        print(f"  ✗ 论文失败: {e}")
        result["paper"] = None

    with open(os.path.join(SCRIPT_DIR, "learning.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return True

def generate_daily():
    """生成 10 条吃瓜日常"""
    print("🍉 生成吃瓜日常...")
    system = """你是生活娱乐编辑。请生成10条轻松有趣的日常内容，涵盖搞笑新闻、奇闻轶事、游戏八卦、美食趣事、科技生活、冷知识等。
每条包含mood心情标签(funny/amaze/useful/hype/nostalgia/cute)和category分类(奇闻/美食/游戏/科技生活/冷知识/趣图/生活)。
输出JSON: {"items": [{"title_cn":"有趣的中文标题","summary_cn":"100-150字中文内容","category":"分类","mood":"心情","tags":["标签"]}, ...]}"""

    user = "请生成10条2026年最新的轻松有趣日常内容，覆盖不同category和mood，让内容有真实感。"

    now = datetime.now(timezone.utc).isoformat()
    try:
        data = ask_deepseek(system, user, temp=0.8, max_tokens=3000)
        items = data.get("items", [])
        for i, item in enumerate(items):
            item["id"] = f"d{i+1:03d}"
            if not item.get("link"):
                import re
                slug = re.sub(r'[^a-zA-Z0-9]+', '-', item.get("title_cn", "daily"))[:80].strip('-').lower()
                item["link"] = "https://example.com/daily/" + slug
            item["published"] = now
        result = {"updated": now, "count": len(items), "items": items}

        with open(os.path.join(SCRIPT_DIR, "daily.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"  ✓ daily.json: {len(items)} 条")
        return True
    except Exception as e:
        print(f"  ✗ 日常生成失败: {e}")
        return False

# ── 主流程 ──
if __name__ == "__main__":
    print("=" * 50)
    print(f"🤖 AI 日报生成 — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)

    ok = 0
    if generate_news():
        ok += 1
    print()
    if generate_daily():
        ok += 1
    print()
    if generate_learning():
        ok += 1

    print(f"\n✅ 完成! {ok}/3 个板块生成成功")
    print(f"📁 输出: {SCRIPT_DIR}")
