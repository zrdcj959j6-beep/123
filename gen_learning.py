import json, os
from datetime import datetime, timezone
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url="https://api.deepseek.com")

def ask(s, u, t=0.6):
    r = client.chat.completions.create(model="deepseek-chat",
        messages=[{"role":"system","content":s},{"role":"user","content":u}],
        temperature=t, max_tokens=2000)
    raw = r.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"): raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)

now = datetime.now(timezone.utc).isoformat()

lt = ask('AI教育者。选一个2026年热门AI术语解释。JSON:{"word":"术语","explanation_cn":"150-250字解释"}',
         '请选一个有深度的2026年AI术语', 0.8)
print(f"Term: {lt['word']}")

lp = ask('AI论文解读专家。虚构一篇2026年6月AI论文做中文解读。JSON:{"title":"英文标题","title_cn":"中文标题","interpretation_cn":"300-500字解读","authors":"作者 et al.","arxiv_id":"2506.xxxxx"}',
         '生成一篇AI领域论文解读', 0.6)
lp["link"] = f"https://arxiv.org/abs/{lp.get('arxiv_id', '2506.00001')}"
lp["published"] = now
print(f"Paper: {lp['title_cn']}")

with open("learning.json", "w", encoding="utf-8") as f:
    json.dump({"updated": now, "term": lt, "paper": lp}, f, ensure_ascii=False, indent=2)
print("Done")
