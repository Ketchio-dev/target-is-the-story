"""출처 한 곳. 전부 정적 HTML, 키도 계정도 JS 렌더링도 없다.

원본은 `data/raw/` 에 캐시하고 커밋하지 않는다. 커밋되는 것은 파싱 결과다.
받아 온 시각과 서버의 Last-Modified 를 같이 적는다 — 연차보고서는 갱신되는 문서다.
"""
import json, os, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
STAMP = os.path.join(RAW, "_fetched.json")
BASE = "https://tribunalsontario.ca/documents"

SOURCES = {
    "ar_2024_25": f"{BASE}/TO/Tribunals_Ontario_2024-2025_Annual_Report.html",
    "ar_2023_24": f"{BASE}/TO/Tribunals_Ontario_2023-2024_Annual_Report.html",
    "ar_2022_23": f"{BASE}/TO/Tribunals_Ontario_2022-2023_Annual_Report.html",
    # 13년 전 같은 기준. 목표가 움직였는지는 이 둘이 있어야 말할 수 있다.
    "std_2013": f"{BASE}/sjto/Service%20Standards%20effective%20September%201%202013.html",
    "std_2012": f"{BASE}/sjto/Service%20Standards%20effective%20April%201%202012.html",
}


def _stamps():
    return json.load(open(STAMP, encoding="utf-8")) if os.path.exists(STAMP) else {}


def fetch(name, refresh=False):
    url = SOURCES[name]
    path = os.path.join(RAW, name + ".html")
    os.makedirs(RAW, exist_ok=True)
    if refresh or not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "target-is-the-story/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body, lm = r.read(), r.headers.get("Last-Modified", "")
        open(path, "wb").write(body)
        st = _stamps()
        st[name] = {"url": url, "bytes": len(body), "last_modified": lm,
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        json.dump(st, open(STAMP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return path


def text(name, refresh=False):
    return open(fetch(name, refresh), encoding="utf-8", errors="replace").read()


def provenance():
    return _stamps()
