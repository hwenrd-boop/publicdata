import urllib.request, json, re, hashlib, sys
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")
import os
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "hwenrd-boop/publicdata"

KEYWORDS = [
    ("%EA%B3%B5%EC%9C%A0%EC%A3%BC%EC%B0%A8", "공유주차"),
    ("%EB%B6%80%EC%84%A4%EC%A3%BC%EC%B0%A8%EC%9E%A5%20%EA%B0%9C%EB%B0%A9", "부설주차장 개방"),
]

# Load existing
existing = {}
try:
    req = urllib.request.Request(
        f"https://raw.githubusercontent.com/{REPO}/main/data/sanction_docs.json",
        headers={"Authorization": f"token {TOKEN}"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        for a in json.loads(r.read()).get("articles", []):
            existing[a["url"]] = a
    print(f"Existing: {len(existing)} docs")
except Exception as e:
    print(f"No existing data: {e}")

# Scrape opengov
new_count = 0
for enc_kw, kw in KEYWORDS:
    url = f"https://opengov.seoul.go.kr/sanction/list?searchKeyword={enc_kw}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "ko-KR,ko;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="ignore")
        links  = re.findall(r'href="/sanction/(\d+)"', html)
        titles = re.findall(r'href="/sanction/\d+"><strong[^>]*>[^<]*</strong><span>(.*?)</span>', html)
        dates  = re.findall(r'class="date"><strong[^>]*>[^<]*</strong>\s*(\d{4}-\d{2}-\d{2})', html)
        depts  = re.findall(r'class="dept"><strong[^>]*>[^<]*</strong>\s*(.*?)</span>', html)
        print(f"'{kw}': {len(titles)} docs found")
        for i, (doc_id, title) in enumerate(zip(links, titles)):
            doc_url = f"https://opengov.seoul.go.kr/sanction/{doc_id}"
            if doc_url not in existing:
                existing[doc_url] = {
                    "id": hashlib.md5(doc_url.encode()).hexdigest()[:8],
                    "title": title.strip(),
                    "url": doc_url,
                    "source": depts[i].strip() if i < len(depts) else "서울시",
                    "published_date": dates[i] if i < len(dates) else TODAY,
                    "summary": f"서울 정보소통광장 결재문서 ({kw})",
                    "category": "공고·결재문서",
                    "collected_date": TODAY,
                }
                new_count += 1
    except Exception as e:
        print(f"Error '{kw}': {e}")

all_docs = sorted(existing.values(), key=lambda x: x["published_date"], reverse=True)
result = {"last_updated": TODAY, "total_count": len(all_docs), "articles": all_docs}
print(f"Total: {len(all_docs)}, new: {new_count}")

# Upload to GitHub
import base64
content_b64 = base64.b64encode(json.dumps(result, ensure_ascii=False, indent=2).encode()).decode()

# Get SHA
sha = ""
try:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/data/sanction_docs.json",
        headers={"Authorization": f"token {TOKEN}"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        sha = json.loads(r.read()).get("sha", "")
except:
    pass

payload = {"message": f"chore: update opengov sanction docs {TODAY}", "content": content_b64}
if sha:
    payload["sha"] = sha

req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/data/sanction_docs.json",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json"},
    method="PUT"
)
with urllib.request.urlopen(req, timeout=15) as r:
    resp = json.loads(r.read())
    print(f"Uploaded: {resp.get('commit', {}).get('sha', 'unknown')[:8]}")
