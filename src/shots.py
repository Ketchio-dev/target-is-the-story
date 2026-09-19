"""앱 화면을 탭별로 찍는다. 영상이 "작동하는 소프트웨어"를 보여야 하기 때문이다.

    python3 src/shots.py

헤드리스 크롬은 클릭을 못 하고 **뷰포트 맨 위**만 찍는다. 그래서 index.html 을 복사해
끝에 작은 스크립트를 덧붙여 탭을 미리 열고, 보고 싶은 카드를 맨 위로 올린 뒤 찍는다.
원본은 건드리지 않는다.
"""
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "web", "index.html")
FIG = os.path.join(ROOT, "figures")
CHROME = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1243/"
    "chrome-headless-shell-mac-arm64/chrome-headless-shell")

TAB = "document.querySelector('[data-t=%s]').click();"
# **중첩에 기대지 않는다.** 앞 판본은 `main > .card` 만 지웠는데 카드가 그 깊이에 있지 않아
# 아무것도 안 지워졌고, 그림이 전부 "페이지 전체"가 됐다. 클릭은 먹히고 격리만 조용히 실패해서
# 겉보기로는 멀쩡했다. 이제 **대상에서 위로 올라가며 형제를 지운다** — 깊이를 몰라도 된다.
LIFT = ("let k=document.getElementById('%s');"
        "k=k.closest('.card')||k;"
        "for(let n=k;n&&n!==document.body;n=n.parentElement){"
        "  [...n.parentElement.children].forEach(sib=>{if(sib!==n)sib.remove();});"
        "}")

# **높이를 박아 두지 않는다.** 사다리를 17행에서 20행으로 늘렸을 때 900px 이 그대로 남아,
# 그림이 아래에서 잘리면서 **이 프로젝트의 헤드라인인 SBT 240일 행이 통째로 빠졌다.**
# 영상이 "허용된 시간 순으로 전부"라고 말하는 동안 화면에는 없는 행이었다.
# 이제 내용 높이를 재서 그만큼 찍는다. h 는 최소값일 뿐이다.
TALL = 4000   # 넉넉히 찍는 높이. 실제 높이는 아래에서 여백을 잘라 정한다.

SHOTS = [
    ("01-ladder", "사다리 — 허용된 시간 순, 막대 안에 달성률", LIFT % "ladder", 900),
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
            # **80ms 는 너무 일렀다.** 페이지가 JS 로 그려지므로 그때는 #ladder 가 아직 없고,
            # closest() 가 터지면서 카드 격리가 조용히 통째로 안 돌았다.
            # 그래서 모든 그림이 "전체 페이지"였고, 사다리는 아래가 잘려 240일 행이 빠졌다.
            body += f"\n<script>setTimeout(()=>{{{js}}},1200);</script>\n"
        open(path, "w", encoding="utf-8").write(body)
        out = os.path.join(FIG, name + ".png")
        # **높이를 재지 말고 넉넉히 찍은 뒤 흰 여백을 잘라낸다.**
        # scrollHeight 를 재는 방법은 카드 격리 스크립트가 돈 뒤의 값을 못 받아 왔다.
        # 여백 잘라내기는 그런 순서 문제가 없다 — 찍힌 픽셀만 보면 된다.
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size=1240,{TALL}", f"--screenshot={out}",
                        "--virtual-time-budget=8000", "file://" + path],
                       capture_output=True, timeout=180)
        if os.path.exists(out):
            try:
                from PIL import Image
                im = Image.open(out).convert("RGB")
                bg = im.getpixel((im.width - 4, im.height - 4))
                bbox = None
                for y in range(im.height - 1, -1, -1):
                    row = im.crop((0, y, im.width, y + 1)).getcolors(maxcolors=1 << 16)
                    if not (len(row) == 1 and row[0][1] == bg):
                        bbox = y + 1
                        break
                if bbox and bbox + 24 < im.height:
                    im.crop((0, 0, im.width, min(im.height, bbox + 24))).save(out)
                    why = f"{why} (여백 잘라 {bbox + 24}px)"
            except Exception as e:
                why = f"{why} (여백 못 잘랐다: {str(e)[:40]})"
        ok = os.path.exists(out) and os.path.getsize(out) > 20000
        if not ok:
            bad.append(name)
        print(f"  {'✓' if ok else '✗'} figures/{name}.png  — {why}")
    shutil.rmtree(tmp, ignore_errors=True)
    if bad:
        sys.exit(f"찍히지 않은 화면: {bad}")


if __name__ == "__main__":
    main()
