"""앱 화면을 탭별로 찍는다. 영상이 "작동하는 소프트웨어"를 보여야 하기 때문이다.

    python3 src/shots.py

헤드리스 크롬은 클릭을 못 하고 **뷰포트 맨 위**만 찍는다. 그래서 index.html 을 복사해
끝에 작은 스크립트를 덧붙여 탭을 미리 열고, 보고 싶은 카드를 맨 위로 올린 뒤 찍는다.
원본은 건드리지 않는다.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "web", "index.html")
FIG = os.path.join(ROOT, "figures")
CHROME = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1243/"
    "chrome-headless-shell-mac-arm64/chrome-headless-shell")

TAB = "document.querySelector('[data-t=%s]').click();"
LIFT = ("const k=document.getElementById('%s').closest('.card');"
        "[...document.querySelectorAll('main > .card')].forEach(c=>{if(c!==k)c.remove();});")

SHOTS = [
    ("01-ladder", "사다리 — 허용된 시간 순, 막대 안에 달성률", "", 900),
    ("02-detail", "한 기준의 원문과 시계 시작점(노란 강조)",
     "document.querySelectorAll('#ladder .b')[15].click();" + LIFT % "detail", 520),
    ("03-rollup", "롤업 재계산 — 고르게 평균 vs 건수 가중",
     TAB % "rollup" + LIFT % "rollup", 760),
    ("04-drift", "13년 전 같은 기준", TAB % "drift" + LIFT % "drift", 900),
]


def main():
    if not os.path.exists(CHROME):
        sys.exit(f"헤드리스 크롬을 못 찾았다: {CHROME}")
    if not os.path.exists(IDX):
        sys.exit("web/index.html 이 없다 — python3 src/export_web.py")
    os.makedirs(FIG, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="titstory-shots-")
    bad = []
    for name, why, js, h in SHOTS:
        path = os.path.join(tmp, name + ".html")
        body = open(IDX, encoding="utf-8").read()
        if js:
            body += f"\n<script>setTimeout(()=>{{{js}}},80);</script>\n"
        open(path, "w", encoding="utf-8").write(body)
        out = os.path.join(FIG, name + ".png")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size=1240,{h}", f"--screenshot={out}",
                        "--virtual-time-budget=8000", "file://" + path],
                       capture_output=True, timeout=120)
        ok = os.path.exists(out) and os.path.getsize(out) > 20000
        if not ok:
            bad.append(name)
        print(f"  {'✓' if ok else '✗'} figures/{name}.png  — {why}")
    shutil.rmtree(tmp, ignore_errors=True)
    if bad:
        sys.exit(f"찍히지 않은 화면: {bad}")


if __name__ == "__main__":
    main()
