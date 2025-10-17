import os, json, re, html
from bs4 import BeautifulSoup
from readability import Document

INP = "data/raw/posts.jsonl"
OUT = "data/clean/posts_clean.jsonl"

def normalize_text(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r'\r\n?', '\n', s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def extract_main(html_text: str) -> str:
    doc = Document(html_text)
    summary = doc.summary(html_partial=True)
    soup = BeautifulSoup(summary, "html.parser")
    for tag in soup(["script","style","nav","footer","header","aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = normalize_text(text)
    # よくある日本語ボイラープレートを軽く除去（必要に応じ調整）
    for ng in ("この記事をシェア", "関連記事", "メニュー", "フッター"):
        text = text.replace(ng, " ")
    return normalize_text(text)

if __name__ == "__main__":
    os.makedirs("data/clean", exist_ok=True)
    with open(INP, "r", encoding="utf-8") as fin, open(OUT, "w", encoding="utf-8") as fout:
        for line in fin:
            item = json.loads(line)
            html_src = item.get("content", {}).get("rendered", "")
            body = extract_main(html_src) if html_src else ""
            rec = {
                "id": item.get("id"),
                "title": item.get("title", {}).get("rendered",""),
                "date": item.get("date"),
                "slug": item.get("slug"),
                "url": item.get("link"),
                "text": body
            }
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"✅ cleaned -> {OUT}")

