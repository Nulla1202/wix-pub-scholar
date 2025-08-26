# scripts/build_bibtex.py
import os, sys, time, json, re
import requests
from pathlib import Path

API_KEY = os.environ.get("SERPAPI_KEY")
AUTHOR_ID = os.environ.get("SCHOLAR_AUTHOR_ID")
LANG = os.environ.get("SCHOLAR_LANG", "en")
BASE_URL = "https://serpapi.com/search"

def fetch_all_articles():
    assert API_KEY and AUTHOR_ID, "SERPAPI_KEY / SCHOLAR_AUTHOR_ID is required"
    all_items = []
    start = 0
    while True:
        params = {
            "engine": "google_scholar_author",
            "author_id": AUTHOR_ID,
            "hl": LANG,
            "start": start,  # offset
            "num": 100       # max 100 per request
        }
        r = requests.get(BASE_URL, params={**params, "api_key": API_KEY}, timeout=60)
        r.raise_for_status()
        data = r.json()
        items = data.get("articles", []) or []
        all_items.extend(items)
        if len(items) < 100:
            break
        start += 100
        time.sleep(1)  # 礼儀として間隔を空ける
    return all_items

def slugify(s):
    return re.sub(r"[^a-zA-Z0-9]+", "-", s.strip())[:60].strip("-").lower()

def bibtex_escape(s):
    return s.replace("&", "\\&").replace("%", "\\%").replace("{", "\\{").replace("}", "\\}")

def as_bibtex_entry(i, item):
    title = item.get("title") or "Untitled"
    authors = item.get("authors") or ""
    year = item.get("year") or ""
    pub = item.get("publication") or ""
    link = item.get("link") or ""  # scholar内の個別ページ
    url = item.get("resources", [{}])[0].get("link", "") if item.get("resources") else ""
    # キー: 先頭著者の姓 + 年 + タイトルスラッグ
    first_author = authors.split(",")[0].split()[-1] if authors else "na"
    key = f"{slugify(first_author)}-{year}-{slugify(title)}"
    # journal/venue は publication 全文を入れておく（BibBaseは柔軟に表示）
    fields = {
        "title": bibtex_escape(title),
        "author": bibtex_escape(authors.replace("...", " et al.")),
        "year": year,
        "journal": bibtex_escape(pub) if pub else None,
        "url": url or link
    }
    # 型は汎用的に @article を採用（会議録も表示上は困らない）
    pairs = [f'{k} = {{{v}}}' for k, v in fields.items() if v]
    return f"@article{{{key},\n  " + ",\n  ".join(pairs) + "\n}\n"

def main():
    out_dir = Path("publications")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "publications.bib"

    arts = fetch_all_articles()
    # 新しい順に並べ替え（year降順）
    def year_of(x): 
        try: return int(x.get("year", 0))
        except: return 0
    arts_sorted = sorted(arts, key=year_of, reverse=True)

    entries = [as_bibtex_entry(i, a) for i, a in enumerate(arts_sorted)]
    text = "% Auto-generated from SerpApi Google Scholar Author API\n" + "\n".join(entries)
    old = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    if text != old:
        out_path.write_text(text, encoding="utf-8")
        print(f"Updated {out_path} with {len(entries)} entries.")
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
