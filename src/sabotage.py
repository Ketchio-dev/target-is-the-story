"""일부러 망가뜨린다. 검사가 알아채는가.

**통과 개수는 품질 지표가 아니다.** 이 프로젝트에서만 검사 셋이 사보타주를 그냥 통과했고
(빈 집합에서 참이 되는 검사, 생성기를 안 돌리는 검사, 캐시 뒤에서 무력해진 사보타주),
그 셋의 원인이 전부 달랐다.

    python3 src/sabotage.py
    python3 src/sabotage.py --only 시계

검출 / 놓침 / 무효를 갈라 찍는다. **놓침은 검사 결함, 무효는 사보타주 결함이다.**
"""
import atexit, hashlib, io, os, re, shutil, signal, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 재진입 차단. check.py 가 이 파일을 **불러오기만** 했다가 포크 폭탄이 났다(가드가 없어서
# 불러오는 즉시 전체가 돌았고, 그게 다시 check.py 를 불렀다). 환경변수는 자식이 물려받으므로
# 어느 경로로 다시 들어와도 여기서 멈춘다.
if os.environ.get("SABOTAGE_RUNNING"):
    sys.exit("사보타주가 이미 돌고 있다 — 재진입을 막는다")
os.environ["SABOTAGE_RUNNING"] = "1"

SABS = [
    ("파서를 즉시 실패시킴", "src/parse_reports.py",
     "def main():", "def main():\n    raise SystemExit(7)", "parse_reports.py 가 종료 코드 0"),
    ("기준 파서를 실패시킴", "src/parse_standards.py",
     "def main():", "def main():\n    raise SystemExit(7)", "parse_standards.py 가 종료 코드 0"),
    ("분석을 실패시킴", "src/analyze.py",
     "ROWS = D[\"rows\"]", "raise SystemExit(7)\nROWS = D[\"rows\"]", "analyze.py 가 종료 코드 0"),
    # 실제로 밟은 함정 1 — 옛 보고서가 조용히 0행이 됐다
    ("옛 보고서 헤더 형식을 다시 못 읽게", "src/parse_reports.py",
     r'fy_p = pick(r"th-\w*fy-p", r"\w*fyp")', r'fy_p = pick(r"th-\w*fy-p")',
     "세 보고서가 각각 100행 이상"),
    # 실제로 밟은 함정 2 — 접사 하나로 롤업 세 행이 사라졌다
    ("롤업 행의 헤더 접사를 다시 놓치게", "src/parse_reports.py",
     r'fy_n = pick(r"th-\w*fy-n", r"\w*fyn")', r'fy_n = pick(r"th-\w+fy-n", r"\w*fyn")',
     "롤업 세 행이 건수와 달성률"),
    # 실제로 밟은 함정 3 — 모든 행이 같은 쓰레기 시계 시작점을 들고 있었다
    ("시계 시작점이 문장 앞머리를 잡게 되돌림", "src/parse_reports.py",
     "    if not m:\n        # 기간 표현이 없으면", "    if False:\n        # 기간 표현이 없으면",
     "시계 시작점이 'Percentage of' 로"),
    ("시계 시작점을 통째로 비움", "src/parse_reports.py",
     '    return c.group(0).strip() if c else ""', '    return ""',
     "시계 시작점 표현이 10가지 이상"),
    # 실제로 밟은 함정 4 — 태그 경계에서 문장이 잘려 기간이 사라졌다
    ("문장 잇기를 끄면 기간이 사라진다", "src/parse_standards.py",
     "        if merged and not re.search(r\"[.:;!?]$\", merged[-1]) and re.match(r\"[a-z(]\", l):",
     "        if False:",
     # tribunal 수는 안 줄어든다 — 줄어드는 것은 **합산 구간**이다. 거기를 겨냥한다.
     "기간이 둘 이상인 기준 문장이 남아 있다"),
    ("사다리 최장 행을 빼 버린다", "src/analyze.py",
     'ladder = [r for r in cur(lambda r: is_first_hearing(r["standard"]))\n          if r["permitted_days"]]',
     'ladder = [r for r in cur(lambda r: is_first_hearing(r["standard"]))\n          if r["permitted_days"] and r["permitted_days"] < 200]',
     "허용시간 배수가 출력과 일치"),
    ("롤업 재계산을 고르게 평균과 같게 만든다", "src/analyze.py",
     'weighted = (sum((r["fy_n"] or 0) * r["fy_pct"] for r in comp) / tot_n) if tot_n else 0',
     'weighted = even',
     "롤업 재계산 차이가 출력과 일치"),
    ("재구성 잔차를 숨긴다", "src/analyze.py",
     '   (잔차 {tot_n - roll[\'fy_n\']:+,.0f}', '   (잔차 없음',
     "재구성 잔차를 출력이 밝힌다"),
    ("건수 0 행을 세지 않는다", "src/analyze.py",
     'zero = cur(lambda r: r["zero_denominator"] and r["target_pct"] is not None)',
     'empty = []',
     "건수 0 행 개수가 출력과 일치"),
    ("드리프트에서 바뀌지 않은 곳을 지운다", "src/analyze.py",
     '(same if abs(d) < 0.5 else moved).append(t)', 'moved.append(t)',
     "드리프트 표에 기준점"),
    ("시계 시작점 변화 표시를 끈다", "src/analyze.py",
     'drift_note = "  ← 시계 시작점도 바뀌었다(직접 비교 불가)"', 'drift_note = ""',
     "시계 시작점이 바뀐 비교를 표가"),
    # --- 블라인드 검토가 잡은 셋. 각각을 다시 심어 본다. ---
    ("드리프트 필터가 'will be scheduled' 를 다시 놓치게", "src/analyze.py",
     r"|hearings?\s+(?:will\s+be\s+)?scheduled", "|hearings? scheduled",
     "드리프트 표에 읽지 못한 칸(nan)이 없다"),
    ("롤업 구성행이 OSETs 를 다시 놓치게", "src/rules.py",
     "r\"proceeds?\\s+to\\s+a\\s+first\\s+(held\\s+hearing\\s+event|held\\s+pre-hearing\\s+event\"",
     "r\"proceeds to a first (held hearing event\"",
     "화면의 롤업 차이가 보고서와"),
    ("N/A 를 다시 건수 0 으로 센다", "src/parse_reports.py",
     '"zero_denominator": num(fy_n) == 0,', '"zero_denominator": (num(fy_n) or 0) == 0,',
     "건수 0 판정이 원본 HTML 의 셀 값과"),
    ("README 의 배수를 손으로 고친다", "README.md",
     r"re:\*\*\d+×\*\* the permitted time", "**999×** the permitted time",
     "README 의 수치가 출력과"),
    ("README 에서 '아무것도 발굴하지 않았다' 를 지운다", "README.md",
     "We uncovered nothing", "We found something remarkable",
     "README 가 '우리는 발굴하지 않았다'"),
    ("템플릿에 수치를 손으로 적는다", "web/page.html",
     "<h1 id=\"h1\"></h1>", "<h1 id=\"h1\">92.0 % met target</h1>",
     "템플릿에 손으로 적은 수가 없다"),
    ("화면이 반올림한 값끼리 빼게 되돌린다", "web/page.html",
     "${R.diff.toFixed(1)} pp", "${(R.weighted - R.even).toFixed(1)} pp",
     "템플릿이 반올림된 값끼리 계산하지 않는다"),
    ("주입을 건너뛰어 화면을 빈 채로 둔다", "src/export_web.py",
     'out = head + OPEN + "\\nconst DATA = " + json.dumps(payload, ensure_ascii=False,\n                                                       separators=(",", ":")) + ";\\n" + CLOSE + tail',
     'out = tpl',
     "index.html 이 이번 실행에서"),
    ("README 의 검사 개수를 실제와 어긋나게 둔다", "README.md",
     r"re:# \d+ checks, at a denominator", "# 999 checks, at a denominator",
     "README 가 말하는 검사·사보타주 개수가 실제와 같다"),
    ("제출 본문의 수치를 슬쩍 고친다", "submission/devpost.md",
     r"re:\*\*240×\*\* the permitted time", "**24×** the permitted time",
     "제출 본문(devpost.md)의 수치가 출력과 일치한다"),
    ("화면이 좁은 규칙의 제 사본을 다시 쓴다", "src/export_web.py",
     "from rules import is_first_hearing",
     "import re as _re\nis_first_hearing = lambda t: bool(_re.search(r\"proceeds to a first|hearings? scheduled within\", t, _re.I))",
     "화면 사다리가 분석과"),
    ("분석이 규칙을 제 파일에 다시 적는다", "src/analyze.py",
     "from rules import FIRST_EVENT, SCHEDULED, is_first_hearing",
     "from rules import FIRST_EVENT, SCHEDULED, is_first_hearing\nSCHEDULED = re.compile(r\"hearings? scheduled within\", re.I)",
     "첫 심리 판정 규칙이 한 벌이다"),
]

# 복원 목록은 **겨냥 대상에서 유도한다.** 손 목록이면 잔해가 남고, 그 잔해가 검사 실패처럼 보인다.
FILES = sorted({f for _d, f, _o, _n, _m in SABS})

bak = tempfile.mkdtemp(prefix="titstory-sab-")
for f in FILES:
    os.makedirs(os.path.join(bak, os.path.dirname(f)), exist_ok=True)
    shutil.copy2(os.path.join(ROOT, f), os.path.join(bak, f))


def restore():
    for f in FILES:
        shutil.copy2(os.path.join(bak, f), os.path.join(ROOT, f))


atexit.register(restore)
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_a: sys.exit(130))

dig = lambda: {f: hashlib.sha1(open(os.path.join(ROOT, f), "rb").read()).hexdigest() for f in FILES}
START = dig()


def check():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "src", "check.py")],
                       capture_output=True, text=True, timeout=1800)
    m = re.search(r"(\d+)/(\d+) 통과", r.stdout)
    return r.stdout, (int(m.group(1)), int(m.group(2))) if m else (None, None)


only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
print(f"\n  대조군 — 아무것도 망가뜨리지 않았을 때")
print(f"  (도는 동안 {', '.join(FILES)} 를 편집하지 마라)")
out, (p0, d0) = check()
if p0 is None or p0 != d0:
    print(f"    대조군이 통과하지 않는다 ({p0}/{d0}). 사보타주 결과는 의미가 없다.")
    sys.exit(2)
print(f"    {p0}/{d0} 통과. 기준 분모 = {d0}\n")

t0 = time.time()
caught, missed, invalid, shrunk = 0, [], [], []
for desc, f, old, new, must in SABS:
    if only and only not in desc:
        continue
    p = os.path.join(ROOT, f)
    s = io.open(p, encoding="utf-8").read()
    if old.startswith("re:"):
        pat = old[3:]
        if not re.search(pat, s):
            invalid.append(desc); print(f"  무효  {desc}\n        정규식이 맞는 곳이 없다: {pat}"); continue
        io.open(p, "w", encoding="utf-8").write(re.sub(pat, new, s, count=1))
    else:
        if old not in s:
            invalid.append(desc); print(f"  무효  {desc}\n        겨냥할 자리를 못 찾았다"); continue
        io.open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
    out, (p1, d1) = check()
    restore()
    line = next((l for l in out.splitlines() if must in l), None)
    hit = bool(line) and line.strip().startswith("BAD")
    caught += hit
    if d1 != d0:
        shrunk.append((desc, d1))
    if not hit:
        missed.append(desc)
    print(f"  {'검출' if hit else '놓침'}  {desc}")
    print(f"        {p1}/{d1}" + (f"  <- 분모가 {d0} 에서 변했다!" if d1 != d0 else "")
          + ("" if hit else f"   겨냥한 검사가 초록이다: {must}"))

n = sum(1 for d, *_ in SABS if not only or only in d)
print(f"\n  {n}건 · {time.time() - t0:.0f}초")
print(f"  {caught}/{n} 검출 · 분모 {d0} 고정")
if missed:
    print(f"  놓침 {len(missed)}건 — **검사 결함인지, 바꾼 것이 동작을 안 바꾼 것인지 가른다.**")
    for m in missed:
        print(f"    · {m}")
if invalid:
    print(f"  무효 {len(invalid)}건 — 코드가 바뀌었는데 이 파일이 안 따라갔다: {invalid}")
if shrunk:
    print(f"  분모가 변한 사보타주 {len(shrunk)}건: {shrunk}")
clob = [f for f in FILES if START.get(f) != dig().get(f)]
if clob:
    print(f"\n  경고: 복원 뒤에도 달라진 파일 {clob}")
sys.exit(1 if (missed or invalid) else 0)
