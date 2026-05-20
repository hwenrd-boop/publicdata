import os, json, re, hashlib
from datetime import datetime, timezone, timedelta
import urllib.request
import xml.etree.ElementTree as ET

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")

QUERIES = [
    "공유주차",
    "부설주차장 개방",
    "공유주차장 운영",
    "부설주차 개방 사업"
]

# Google News에서 opengov.seoul.go.kr 문서 검색용 쿼리
GOOGLE_OPENGOV_QUERIES = [
    "site:opengov.seoul.go.kr 공유주차",
    "site:opengov.seoul.go.kr 부설주차장 개방",
]

def fetch_google_news(query):
    import urllib.parse
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except Exception as e:
        print(f"Error fetching {query}: {e}")
        return None

def parse_feed(xml_bytes):
    if not xml_bytes:
        return []
    items = []
    try:
        root = ET.fromstring(xml_bytes)
        for item in root.findall(".//item")[:8]:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_el = item.find("pubDate")
            source_el = item.find("source")
            desc_el = item.find("description")
            if title_el is None or link_el is None:
                continue
            title = re.sub(r"<[^>]+>", "", title_el.text or "").strip()
            link = (link_el.text or "").strip()
            source = source_el.text.strip() if source_el is not None and source_el.text else "언론사 미상"
            desc = re.sub(r"<[^>]+>", "", desc_el.text or "").strip()[:150] if desc_el is not None else ""
            pub_date = TODAY
            if pub_el is not None and pub_el.text:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_el.text)
                    pub_date = dt.astimezone(KST).strftime("%Y-%m-%d")
                except:
                    pass
            uid = hashlib.md5(link.encode()).hexdigest()[:8]
            items.append({
                "id": uid, "title": title, "url": link,
                "source": source, "published_date": pub_date,
                "summary": desc, "category": "뉴스",
                "collected_date": TODAY
            })
    except Exception as e:
        print(f"Parse error: {e}")
    return items

# Load existing
existing = {}
if os.path.exists("data/articles.json"):
    with open("data/articles.json", encoding="utf-8") as f:
        data = json.load(f)
        for a in data.get("articles", []):
            existing[a["url"]] = a

# Collect new
new_count = 0
for q in QUERIES:
    print(f"Fetching: {q}")
    xml = fetch_google_news(q)
    items = parse_feed(xml)
    for item in items:
        if item["url"] not in existing:
            existing[item["url"]] = item
            new_count += 1
    print(f"  +{len(items)} items")

# Google News에서 opengov.seoul.go.kr 문서 검색
print("Fetching OpenGov docs via Google News...")
for q in GOOGLE_OPENGOV_QUERIES:
    xml = fetch_google_news(q)
    items = parse_feed(xml)
    for item in items:
        if item["url"] not in existing:
            item["category"] = "공고·결재문서"
            item["source"] = "서울 정보소통광장"
            existing[item["url"]] = item
            new_count += 1
    print(f"  Google+OpenGov '{q}': +{len(items)} items")


all_articles = sorted(existing.values(), key=lambda x: x["published_date"], reverse=True)
os.makedirs("data", exist_ok=True)
with open("data/articles.json", "w", encoding="utf-8") as f:
    json.dump({"last_updated": TODAY, "total_count": len(all_articles), "articles": all_articles}, f, ensure_ascii=False, indent=2)
print(f"Total: {len(all_articles)} articles ({new_count} new)")

# Build HTML
articles_json = json.dumps(all_articles, ensure_ascii=False)
html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>공유주차·부설주차장 개방 뉴스 모음</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f7fa;color:#333}}
header{{background:#1a73e8;color:#fff;padding:24px 20px}}
header h1{{font-size:1.4rem;font-weight:700}}
header p{{font-size:.85rem;opacity:.85;margin-top:4px}}
.stats{{background:#fff;padding:12px 20px;border-bottom:1px solid #e0e0e0;font-size:.85rem;color:#555}}
.filters{{padding:16px 20px;display:flex;gap:8px;flex-wrap:wrap}}
.filter-btn{{padding:6px 16px;border:1.5px solid #1a73e8;border-radius:20px;background:#fff;color:#1a73e8;cursor:pointer;font-size:.85rem;transition:.2s}}
.filter-btn.active{{background:#1a73e8;color:#fff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;padding:0 20px 20px}}
.card{{background:#fff;border-radius:12px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:.2s}}
.card:hover{{box-shadow:0 4px 16px rgba(0,0,0,.13)}}
.card-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}}
.badge{{font-size:.75rem;padding:3px 8px;border-radius:10px;background:#e8f0fe;color:#1a73e8;font-weight:600}}
.date{{font-size:.78rem;color:#888}}
.card h3{{font-size:.95rem;font-weight:600;line-height:1.5;margin-bottom:8px}}
.card h3 a{{color:#1a2a3a;text-decoration:none}}
.card h3 a:hover{{color:#1a73e8}}
.card p{{font-size:.83rem;color:#666;line-height:1.55}}
footer{{text-align:center;padding:24px;font-size:.83rem;color:#999}}
</style>
</head>
<body>
<header>
  <h1>공유주차·부설주차장 개방 뉴스 모음</h1>
  <p>마지막 업데이트: {TODAY} &nbsp;|&nbsp; 총 {len(all_articles)}건 수집</p>
</header>
<div class="stats">오늘 {new_count}건 신규 수집</div>
<div class="filters">
  <button class="filter-btn active" onclick="filter(this,'')">전체</button>
  <button class="filter-btn" onclick="filter(this,'뉴스')">뉴스</button>
  <button class="filter-btn" onclick="filter(this,'공고·결재문서')">공고·결재문서</button>
</div>
<div class="grid" id="grid"></div>
<footer>매일 오전 9시 자동 수집됩니다 (GitHub Actions)</footer>
<script>
const DATA={articles_json};
function render(cat){{
  const g=document.getElementById('grid');
  const items=cat?DATA.filter(a=>a.category===cat):DATA;
  g.innerHTML=items.map(a=>`<div class="card">
    <div class="card-top"><span class="badge">${{a.source}}</span><span class="date">${{a.published_date}}</span></div>
    <h3><a href="${{a.url}}" target="_blank" rel="noopener">${{a.title}}</a></h3>
    ${{a.summary?`<p>${{a.summary}}</p>`:''}}
  </div>`).join('');
}}
function filter(btn,cat){{
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');render(cat);
}}
render('');
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("index.html written")
