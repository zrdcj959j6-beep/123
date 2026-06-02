#!/usr/bin/env python3
"""
AI 学习内容生成脚本
- 每天生成一个 AI 术语解释
- 从 ArXiv CS.AI RSS 中选一篇论文做中文解读
- 输出到 learning.json
"""

import feedparser
import json
import os
import random
import re
import sys
import urllib.request
import ssl
from datetime import datetime, timezone
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────
LEARNING_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learning.json")
ARXIV_RSS = "https://rss.arxiv.org/rss/cs.AI"
FEED_UA = "AIDailyBot/1.0 (News Aggregator; +https://github.com)"
FEED_TIMEOUT = 20

# 全局 UA 兜底
feedparser.USER_AGENT = FEED_UA

# 如果 API 不可用，使用这些备用术语
FALLBACK_TERMS = [
    {
        "word": "Transformer",
        "explanation_cn": "Transformer 是一种基于自注意力机制的神经网络架构，由 Google 在 2017 年提出。它抛弃了传统的 RNN 结构，通过并行计算实现高效的序列建模，是现代大语言模型（如 GPT、BERT）的核心基础。",
    },
    {
        "word": "Diffusion Model（扩散模型）",
        "explanation_cn": "扩散模型是一种生成模型，通过逐步向数据添加噪声（前向过程），再学习逆向去噪（反向过程）来生成新数据。Stable Diffusion 和 DALL-E 等图像生成模型均基于此原理。",
    },
    {
        "word": "RLHF（基于人类反馈的强化学习）",
        "explanation_cn": "RLHF 是一种训练方法：先用人类偏好数据训练奖励模型，再用强化学习（如 PPO）微调语言模型，使其输出更符合人类期望。ChatGPT 的成功很大程度上归功于 RLHF。",
    },
    {
        "word": "Mixture of Experts（MoE，混合专家）",
        "explanation_cn": "MoE 是一种模型架构，将网络分成多个"专家"子网络，每次只激活其中一部分。这大大降低了推理计算量，使得在相同算力下可以训练规模更大的模型。Mixtral 和 GPT-4 据信使用了此技术。",
    },
    {
        "word": "RAG（检索增强生成）",
        "explanation_cn": "RAG 将信息检索系统与生成模型结合：先从外部知识库检索相关文档，再让模型基于这些文档生成答案。既能利用模型的语言能力，又减少了幻觉（hallucination）问题。",
    },
    {
        "word": "LoRA（低秩适应）",
        "explanation_cn": "LoRA 是一种参数高效微调方法，通过在预训练模型的权重矩阵旁添加低秩分解矩阵来进行微调。大幅降低了显存需求和训练成本，是目前最主流的大模型微调技术之一。",
    },
    {
        "word": "Agent（AI 智能体）",
        "explanation_cn": "AI Agent 是能够自主感知环境、制定计划、执行工具调用并迭代优化的大模型应用。它不再只是对话，而是能真正'做事'——搜索网页、写代码、调用 API 等。",
    },
    {
        "word": "Quantization（量化）",
        "explanation_cn": "量化是将模型参数从高精度（如 FP16）压缩到低精度（如 INT4/INT8）的技术。显著减小模型体积和推理成本，是本地运行大模型的关键技术。GGUF 和 AWQ 是常见的量化格式。",
    },
    {
        "word": "Attention Mechanism（注意力机制）",
        "explanation_cn": "注意力机制让模型在处理序列时能动态地关注不同位置的信息。自注意力（Self-Attention）是 Transformer 的核心，通过计算序列内两两之间的关联权重，捕捉长距离依赖关系。",
    },
    {
        "word": "Multimodal Model（多模态模型）",
        "explanation_cn": "多模态模型能同时理解和生成多种类型的数据（文本、图像、音频、视频）。GPT-4V、Gemini 和 Claude 3 都是多模态模型，代表了 AI 从单一文本走向综合感知的趋势。",
    },
]

# OpenAI 客户端
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com")


# ── 工具函数 ──────────────────────────────────────────

def _fetch_rss(url, timeout=FEED_TIMEOUT):
    """带 UA 和超时的 RSS 抓取，使用 requests 避免 urllib DNS 问题"""
    try:
        import requests as req
        resp = req.get(url, headers={"User-Agent": FEED_UA}, timeout=timeout)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception as e:
        result = feedparser.parse("")
        result.bozo = True
        result.bozo_exception = e
        return result


def fetch_arxiv_papers():
    """抓取 ArXiv CS.AI 最新论文"""
    papers = []
    try:
        resp = _fetch_rss(ARXIV_RSS)
        for entry in resp.entries[:20]:  # 取前 20 篇
            arxiv_id = ""
            if entry.get("id"):
                # arxiv id 格如 http://arxiv.org/abs/2506.12345v1
                # 用正则安全提取 "2506.12345" 部分
                m = re.match(r"^.*?(\d{4}\.\d{4,5})(?:v\d+)?$", entry["id"])
                arxiv_id = m.group(1) if m else entry["id"].split("/")[-1]

            papers.append({
                "title": entry.get("title", "").strip().replace("\n", " "),
                "arxiv_id": arxiv_id,
                "link": entry.get("link", ""),
                "summary_original": entry.get("summary", entry.get("description", "")),
                "authors": entry.get("author", ""),
                "published": entry.get("published", ""),
            })
        print(f"  ✓ ArXiv: {len(papers)} 篇论文")
    except Exception as e:
        print(f"  ✗ ArXiv 抓取失败: {e}", file=sys.stderr)
    return papers


def generate_term_with_ai():
    """使用 OpenAI 生成 AI 术语解释"""
    system_prompt = """你是一个 AI 教育者。请给出一个当前热门或重要的 AI/机器学习术语，并用通俗易懂的中文解释它。
解释应包括：定义、为什么重要、典型应用场景。控制在 150-250 字。

输出 JSON 格式：
{"word": "Term Name (英文/中文)", "explanation_cn": "中文解释"}"""

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请随机选一个2024-2026年热门的AI术语，不要选太基础的（如'机器学习'、'深度学习'），选有深度的。"},
            ],
            temperature=0.8,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"): raw = raw[:-3]
            raw = raw.strip()
        data = json.loads(raw)
        return {
            "word": data.get("word", ""),
            "explanation_cn": data.get("explanation_cn", ""),
        }
    except Exception as e:
        print(f"  DeepSeek 术语生成失败: {type(e).__name__}: {e}", file=sys.stderr)
        return random.choice(FALLBACK_TERMS)


def generate_paper_interpretation(paper):
    """使用 OpenAI 对论文做中文解读"""
    system_prompt = """你是一个 AI 研究论文解读专家。请用中文对以下论文进行通俗解读，让非专业读者也能理解。
包括：
1. 论文要解决什么问题
2. 核心方法/创新点
3. 主要发现或效果
4. 一句话总结（这条研究的实际意义）

控制在 300-500 字。

输出 JSON 格式：
{"title_cn": "论文中文标题（简洁）", "interpretation_cn": "中文解读"}"""

    user_prompt = f"""论文标题: {paper['title']}
作者: {paper.get('authors', '未知')}
摘要: {paper.get('summary_original', '（无摘要）')[:1000]}"""

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=1000,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"): raw = raw[:-3]
            raw = raw.strip()
        data = json.loads(raw)
        return {
            "title_cn": data.get("title_cn", paper["title"]),
            "interpretation_cn": data.get("interpretation_cn", ""),
        }
    except Exception as e:
        print(f"  DeepSeek 论文解读失败: {type(e).__name__}: {e}", file=sys.stderr)
        return {
            "title_cn": paper["title"],
            "interpretation_cn": f"（自动解读生成失败）\n\n论文链接: {paper['link']}\n摘要: {paper.get('summary_original', '')[:300]}...",
        }


def pick_best_paper(papers):
    """从论文列表中挑选最有解读价值的（启发式规则）"""
    if not papers:
        return None

    # 优先选择标题包含热门关键词的
    hot_keywords = [
        "agent", "reasoning", "multimodal", "alignment", "safety",
        "efficient", "diffusion", "robot", "code", "planning",
        "retrieval", "rag", "fine-tuning", "instruction", "rlhf",
        "transformer", "vision", "video", "generation", "editing",
        "benchmark", "scaling", "chain-of-thought", "tool",
    ]
    scored = []
    for p in papers:
        score = 0
        title_lower = p["title"].lower()
        for kw in hot_keywords:
            if kw in title_lower:
                score += 1
        # 标题长度适中的加分（太短信息少，太长偏技术）
        tlen = len(p["title"])
        if 50 <= tlen <= 150:
            score += 1
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    # 在前 5 名中随机选一篇（让每天的内容有变化）
    top = scored[:max(5, len(scored)//2)]
    return random.choice(top)[1]


# ── 主逻辑 ────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"AI 学习内容生成 — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    result = {"updated": datetime.now(timezone.utc).isoformat()}

    # 1. 生成 AI 术语解释
    print("\n📖 生成 AI 术语...")
    term = generate_term_with_ai()
    result["term"] = term
    print(f"  术语: {term['word']}")

    # 2. 抓取 ArXiv 论文
    print("\n📄 抓取 ArXiv 论文...")
    papers = fetch_arxiv_papers()

    # 3. 挑选并解读论文
    print("\n📝 解读论文...")
    chosen = pick_best_paper(papers)
    if chosen:
        interpretation = generate_paper_interpretation(chosen)
        result["paper"] = {
            "title": chosen["title"],
            "title_cn": interpretation["title_cn"],
            "interpretation_cn": interpretation["interpretation_cn"],
            "link": chosen["link"],
            "arxiv_id": chosen.get("arxiv_id", ""),
            "authors": chosen.get("authors", ""),
            "published": chosen.get("published", ""),
        }
        print(f"  论文: {chosen['title'][:80]}...")
    else:
        result["paper"] = None
        print("  ⚠ 未找到论文")

    # 4. 保存
    with open(LEARNING_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ learning.json 已生成")
    print(f"📁 路径: {LEARNING_JSON_PATH}")


if __name__ == "__main__":
    main()
