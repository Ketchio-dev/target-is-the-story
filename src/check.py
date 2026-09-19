"""검사. **분모 고정** — 어떤 실패에도 개수가 줄지 않는다.

검사를 이름으로 고른다. 인덱스로 고르면 항목을 끼울 때 라벨과 결과가 한 칸씩 어긋난다.
여기 있는 검사 대부분은 **내가 실제로 밟은 함정**에서 나왔다:
조용히 0행이 된 옛 보고서, 접사 하나 때문에 사라진 롤업 행,
모든 행이 같은 쓰레기를 들고 있던 시계 시작점, 태그 경계에서 잘려 기간이 사라진 문장.

    python3 src/check.py
"""
import json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KPI = os.path.join(ROOT, "data", "kpi.json")
STD = os.path.join(ROOT, "data", "standards.json")
TPL = os.path.join(ROOT, "web", "page.html")
IDX = os.path.join(ROOT, "web", "index.html")
README = os.path.join(ROOT, "README.md")

NAMES = [
    "kpi.json 과 standards.json 이 있다",
    "parse_reports.py 가 종료 코드 0",
    "parse_standards.py 가 종료 코드 0",
    "analyze.py 가 종료 코드 0",
    "세 보고서가 각각 100행 이상이다",
    "롤업 세 행이 건수와 달성률을 달고 있다",
    "시계 시작점이 'Percentage of' 로 시작하지 않는다",
    "시계 시작점 표현이 10가지 이상이다",
    "사다리의 최단·최장이 출력과 일치한다",
    "허용시간 배수가 출력과 일치한다",
    "롤업 재계산 차이가 출력과 일치한다",
    "재구성 잔차를 출력이 밝힌다",
    "건수 0 행 개수가 출력과 일치한다",
    "'보고 안 함' 행을 건수 0 과 갈라 센다",
    "건수 0 판정이 원본 HTML 의 셀 값과 일치한다",
    "2012·2013 기준이 tribunal 5곳 이상에서 읽혔다",
    "기간이 둘 이상인 기준 문장이 남아 있다",
    "드리프트 표에 기준점(바뀌지 않은 곳)이 하나 이상 있다",
    "드리프트 표가 비교 가능한 tribunal 을 하나도 빠뜨리지 않는다",
    "드리프트 표에 읽지 못한 칸(nan)이 없다",
    "시계 시작점이 바뀐 비교를 표가 표시한다",
    "README 의 수치가 출력과 일치한다",
    "README 가 '우리는 발굴하지 않았다' 를 말한다",
    "템플릿에 손으로 적은 수가 없다",
    "index.html 이 이번 실행에서 다시 쓰였다",
    "화면의 롤업 차이가 보고서와 같은 값이다",
    "템플릿이 반올림된 값끼리 계산하지 않는다",
    "README 가 말하는 검사·사보타주 개수가 실제와 같다",
    "제출 본문(devpost.md)의 수치가 출력과 일치한다",
    "화면 사다리가 분석과 같은 행 수·같은 시계 시작점 가짓수를 쓴다",
    "첫 심리 판정 규칙이 한 벌이다(제 사본을 둔 파일이 없다)",
    "어느 문서도 검사·사보타주 개수를 틀리게 적지 않았다",
    "화면의 롤업 수치가 analyze 출력과 전부 일치한다",
    "사다리 그림이 모든 행을 담고 있다(아래가 잘리지 않았다)",
]
result = {n: (False, "실행되지 않음") for n in NAMES}
assert len(NAMES) == len(set(NAMES)), "검사 이름이 중복된다"


def NAME(n):
    if n not in result:
        raise SystemExit(f"검사 이름이 목록에 없다: {n!r}")
    return n


def ok(name, cond, detail=""):
    result[name] = (bool(cond), detail)


def run(script, *a):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "src", script), *a],
                       capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout, r.stderr


def one(pat, text, flags=0):
    m = re.search(pat, text, flags)
    return m.groups() if m else None


ok(NAME("kpi.json 과 standards.json 이 있다"), os.path.exists(KPI) and os.path.exists(STD),
   "없으면 python3 src/parse_reports.py && python3 src/parse_standards.py")

# **낡은 데이터 위에서 통과하지 못하게 한다.** 파서를 망가뜨렸더니 파서 검사만 BAD 가 되고,
# 그 아래 데이터 검사들은 지난번 kpi.json 을 읽어 전부 초록이었다.
# 검사가 채점할 파일은 **검사가 지우고 다시 만든 것**이어야 한다.
for _f in (KPI, STD):
    if os.path.exists(_f):
        os.remove(_f)

rc, _o, err = run("parse_reports.py")
ok(NAME("parse_reports.py 가 종료 코드 0"), rc == 0, err.strip()[-150:])
rc, _o, err = run("parse_standards.py")
ok(NAME("parse_standards.py 가 종료 코드 0"), rc == 0, err.strip()[-150:])
rc_a, out, err_a = run("analyze.py")
ok(NAME("analyze.py 가 종료 코드 0"), rc_a == 0, err_a.strip()[-150:])

K = json.load(open(KPI, encoding="utf-8")) if os.path.exists(KPI) else {"rows": []}
S = json.load(open(STD, encoding="utf-8")) if os.path.exists(STD) else {"rows": []}
ROWS = K["rows"]
CUR = [r for r in ROWS if r["source"] == "ar_2024_25"]

# 보고서 판본마다 헤더 이름이 다르다. 한 판만 다루면 **옛 보고서가 조용히 0행**이 된다.
per = {}
for r in ROWS:
    per[r["source"]] = per.get(r["source"], 0) + 1
thin = [f"{k}={v}" for k, v in per.items() if v < 100]
ok(NAME("세 보고서가 각각 100행 이상이다"), len(per) >= 3 and not thin,
   f"보고서 {len(per)}개 · 빈약 {thin}")

# 접사 하나(`th-fy-n` vs `th-sbtfy-n`) 때문에 헤드라인 세 행이 통째로 사라졌던 자리.
roll = [r for r in CUR if "Tribunals Ontario meets" in r["standard"]
        and r["fy_n"] and r["fy_pct"] is not None]
ok(NAME("롤업 세 행이 건수와 달성률을 달고 있다"), len(roll) >= 3,
   f"{len(roll)}개만 읽혔다 — 헤더 접사를 의심한다")

# `not bad` 는 모집단이 사라지면 참이다. **볼 것이 있었는지 먼저 센다.**
have_clock = [r for r in CUR if r["clock_start"]]
bad_clock = [r["clock_start"] for r in have_clock
             if r["clock_start"].lower().startswith(("of hearings", "of cases", "that "))]
ok(NAME("시계 시작점이 'Percentage of' 로 시작하지 않는다"),
   len(have_clock) >= 20 and not bad_clock,
   f"시계 시작점이 있는 행 {len(have_clock)}개 · 앞머리를 잡은 것 {len(bad_clock)}개 {bad_clock[:2]}")

clocks = {r["clock_start"] for r in CUR if r["clock_start"] and r["permitted_days"]}
ok(NAME("시계 시작점 표현이 10가지 이상이다"), len(clocks) >= 10, f"{len(clocks)}가지")

g = one(r"둘 다 100 % 달성: (\w+) ([^(]+)\(n=([\d,]+)\)\s+vs\s+(\w+) ([^(]+)\(n=([\d,]+)\)", out)
ok(NAME("사다리의 최단·최장이 출력과 일치한다"),
   bool(g) and g[0] != g[3], f"{g[0] + '/' + g[3] if g else '?'}")

r_ratio = one(r"허용된 시간의 비: (\d+)배", out)
lad = [r for r in CUR if r["permitted_days"] and r["fy_pct"] == 100]
calc = (max(r["permitted_days"] for r in lad) / min(r["permitted_days"] for r in lad)) if lad else 0
ok(NAME("허용시간 배수가 출력과 일치한다"),
   bool(r_ratio) and abs(float(r_ratio[0]) - calc) < 1,
   f"출력 {r_ratio[0] if r_ratio else '?'} vs 데이터 {calc:.0f}")

g = one(r"고르게 평균\(각주 방법, \d+곳\)\s+([\d.]+) %.*?건수로 가중[^\d-]*([\d.]+) %\s+차이 ([+-][\d.]+) pp", out, re.S)
# 출력 안의 세 수가 서로 맞는지만 보면 **둘을 같은 값으로 만들어도 통과한다**
# (`weighted = even` 으로 바꿔 보니 0.0 = 0.0 으로 초록이었다).
# 그래서 가중 평균을 **검사가 데이터에서 독립적으로 다시 구해** 맞춰 본다.
# **검사가 스크립트와 같은 정규식을 쓰면 같은 버그를 공유한다.** 실제로 그래서
# OSETs 누락 사보타주를 놓쳤다. 여기서는 더 **넓은** 기준으로 독립적으로 고른다.
comp_rows = [r for r in CUR
             if re.search(r"\bproceeds?\b.*\bfirst\b", r["standard"], re.I)
             and r["fy_pct"] is not None]
tot_n = sum(r["fy_n"] or 0 for r in comp_rows)
indep = (sum((r["fy_n"] or 0) * r["fy_pct"] for r in comp_rows) / tot_n) if tot_n else None
ok(NAME("롤업 재계산 차이가 출력과 일치한다"),
   bool(g) and indep is not None
   and abs((float(g[1]) - float(g[0])) - float(g[2])) < 0.15
   and abs(float(g[1]) - indep) < 0.15,
   f"출력 {g if g else '?'} · 검사가 독립으로 구한 가중평균 {indep if indep is None else round(indep, 1)}")

ok(NAME("재구성 잔차를 출력이 밝힌다"), "잔차" in out and re.search(r"잔차 [+-][\d,]+", out) is not None,
   "재구성 합과 보고서 분모가 다르면 **그 차이를 찍어야** 한다")

g = one(r"건수 0 위에 퍼센트를 얹은 행: (\d+)개", out)
zeros = [r for r in CUR if r["zero_denominator"] and r["target_pct"] is not None]
ok(NAME("건수 0 행 개수가 출력과 일치한다"),
   bool(g) and int(g[0]) == len(zeros), f"출력 {g[0] if g else '?'} vs 데이터 {len(zeros)}")

# **"N/A" 를 0 이라고 부르는 것은 이 프로젝트가 지적하려던 바로 그 잘못이다.**
# 앞 판본이 둘을 합쳐 9라고 적었고, 블라인드 검토가 잡았다.
# 파서와 보고서가 **같이** 틀리면 위 대조는 통과한다. 원본 HTML 을 직접 읽어 맞춘다.
raw_html = open(os.path.join(ROOT, "data", "raw", "ar_2024_25.html"), encoding="utf-8",
                errors="replace").read()
row_bodies = {m.group(1): m.group(3) for m in
              re.finditer(r'<th id="(\w+)"[^>]*scope="row">(.*?)</th>(.*?)</tr>', raw_html, re.S)}
raw_zero = 0
for r in CUR:
    if r["target_pct"] is None:
        continue
    body = row_bodies.get(r["row_id"], "")
    cells = {h2: re.sub(r"<[^>]+>", "", v).strip()
             for h, v in re.findall(r'<td headers="([^"]*)"[^>]*>(.*?)</td>', body, re.S)
             for h2 in h.split()}
    n_cell = next((v for k, v in cells.items() if re.fullmatch(r"th-\w*fy-n", k)), "")
    if n_cell == "0":
        raw_zero += 1
ok(NAME("건수 0 판정이 원본 HTML 의 셀 값과 일치한다"),
   raw_zero == len(zeros) and raw_zero >= 1,
   f"원본에서 fy-n 이 문자 '0' 인 행 {raw_zero}개 vs 파서 판정 {len(zeros)}개")

gn = one(r"결과를 '[^']*' 로 적은 행: (\d+)개", out)
notrep = [r for r in CUR if r["not_reported"] and r["target_pct"] is not None]
ok(NAME("'보고 안 함' 행을 건수 0 과 갈라 센다"),
   bool(gn) and int(gn[0]) == len(notrep) and len(zeros) != len(notrep),
   f"출력 {gn[0] if gn else '?'} vs 데이터 {len(notrep)} (건수 0 은 {len(zeros)})")

tribs = {r["tribunal"] for r in S["rows"]}
ok(NAME("2012·2013 기준이 tribunal 5곳 이상에서 읽혔다"), len(tribs) >= 5,
   f"{len(tribs)}곳: {sorted(tribs)}")

# 문장이 태그 경계에서 잘리면 **기간 하나가 조용히 사라진다.** tribunal 수는 그대로라서
# 위 검사로는 안 잡힌다. "통지 30일 + 그로부터 180일" 같은 합산 구간이 남아 있는지 본다.
multi = [r for r in S["rows"] if len([d for d in r["durations"] if d["days"]]) >= 2]
ok(NAME("기간이 둘 이상인 기준 문장이 남아 있다"), len(multi) >= 2,
   f"{len(multi)}개 — 0이면 문장이 태그 경계에서 잘렸다는 뜻이다")

ok(NAME("드리프트 표에 기준점(바뀌지 않은 곳)이 하나 이상 있다"),
   re.search(r"13년째 같은 곳 \[[^\]]+\]", out) and "13년째 같은 곳 []" not in out,
   "전부 움직였다고 나오면 비교 기준이 없다 — 파싱을 의심한다")

# **필터가 반례를 지워도 위 검사는 초록이다** — HRTO 하나만 남아도 "기준점이 있다"는
# 참이기 때문이다. 그래서 **덮개**를 따로 센다: 옛 기준과 현재 기준을 둘 다 가진
# tribunal 은 전부 표에 있어야 한다. 기준은 파생 목록이 아니라 **데이터**다.
# 덮개 기준은 analyze.py 의 **포함 규칙을 쓰지 않는다** — 같은 정규식을 쓰면 같은 버그를
# 공유한다. 대신 **배타 규칙**으로 고른다: 기간이 있고, "발부/결정/권고/통지"에 관한
# 문장이 아닌 것. 서로 다른 방식으로 같은 집합에 닿아야 한다.
ISSUING = re.compile(r"\b(issued|issue|decision|order|recommendation|advise|reasons)\b", re.I)
old_tribs = {r["tribunal"] for r in S["rows"]
             if any(d["days"] for d in r["durations"])
             and not ISSUING.search(r["sentence"])}
now_tribs = {r["tribunal"] for r in CUR if r["permitted_days"]}
comparable = old_tribs & now_tribs
in_table = set(re.findall(r"^  ([A-Z]+)\s+[\d nan]+", out, re.M))
missing_t = sorted(comparable - in_table)
ok(NAME("드리프트 표가 비교 가능한 tribunal 을 하나도 빠뜨리지 않는다"),
   not missing_t and len(comparable) >= 4,
   f"비교 가능 {sorted(comparable)} · 표에 없는 것 {missing_t}")

# `nan` 은 "그 해 기준을 못 읽었다"는 뜻인데 표는 그 옆에 변화량을 적는다.
# 즉 **비교할 수 없는 것을 비교로 그린다.** 필터가 문장을 놓치면 여기서 드러난다.
ok(NAME("드리프트 표에 읽지 못한 칸(nan)이 없다"),
   "nan" not in out,
   "nan 이 있으면 그 해 기준을 못 읽은 것이다 — 변화량을 옆에 적으면 안 된다")

ok(NAME("시계 시작점이 바뀐 비교를 표가 표시한다"), "시계 시작점도 바뀌었다" in out,
   "날짜만 견주고 시계 시작점 변화를 안 밝히면 다른 구간을 비교하게 된다")

readme = open(README, encoding="utf-8").read() if os.path.exists(README) else ""
pairs = []
for label, po, pd_ in (
    ("배수", r"허용된 시간의 비: (\d+)배", r"\*\*(\d+)×\*\* the permitted time"),
    ("건수0", r"건수 0 위에 퍼센트를 얹은 행: (\d+)개", r"\*\*(\d+) row\*\* reports a percentage on no cases"),
):
    a, b = one(po, out), one(pd_, readme)
    if not (a and b and a[0] == b[0]):
        pairs.append(f"{label}: 출력 {a[0] if a else '?'} vs README {b[0] if b else '?'}")
ok(NAME("README 의 수치가 출력과 일치한다"), not pairs, "; ".join(pairs))

ok(NAME("README 가 '우리는 발굴하지 않았다' 를 말한다"),
   "uncovered nothing" in readme.lower() or "did not uncover" in readme.lower(),
   "전부 그들이 낸 수다. 그 문장이 없으면 과장이 된다")

nums = []
if os.path.exists(TPL):
    body = re.sub(r"<style>.*?</style>", "", open(TPL, encoding="utf-8").read(), flags=re.S)
    nums = sorted({n for n in re.findall(r"\b\d+\.\d+\b", body)})
ok(NAME("템플릿에 손으로 적은 수가 없다"), os.path.exists(TPL) and not nums,
   f"남은 소수 {nums[:6]}" if nums else ("web/page.html 이 없다" if not os.path.exists(TPL) else ""))

before = os.path.getmtime(IDX) if os.path.exists(IDX) else 0
time.sleep(1.1)
rc_w, _ow, err_w = run("export_web.py")
why, good = "", False
if rc_w != 0:
    why = f"export_web.py 실패: {err_w.strip()[-120:]}"
elif not os.path.exists(IDX):
    why = "web/index.html 이 없다"
elif os.path.getmtime(IDX) <= before:
    why = "돌렸는데 index.html 이 갱신되지 않았다 — 옛 화면이 남아 있다"
else:
    # **문자열을 세지 말고 파싱한다.** 키 이름이 바뀌면 개수가 조용히 0이 되고,
    # 그러면 "주입이 안 됐다" 와 "세는 법이 틀렸다" 가 구분되지 않는다.
    b = open(IDX, encoding="utf-8").read()
    m = re.search(r"const DATA = (\{.*?\});\n/\*DATA_END\*/", b, re.S)
    if not m:
        why = "주입 블록을 못 찾았다 (const DATA = null 그대로일 수 있다)"
    else:
        try:
            inj = json.loads(m.group(1))
            n = len(inj.get("ladder") or [])
            good, why = (n >= 10), f"사다리 {n}행 주입됨"
        except json.JSONDecodeError as e:
            why = f"주입된 JSON 이 깨졌다: {e}"
ok(NAME("index.html 이 이번 실행에서 다시 쓰였다"), good, why)

# 반올림한 값끼리 빼면 0.1 이 갈린다. 두 문서가 같은 수를 말하는지 본다.
pg_diff = None
if os.path.exists(IDX):
    mm = re.search(r'"diff":(-?[\d.]+)', open(IDX, encoding="utf-8").read())
    pg_diff = float(mm.group(1)) if mm else None
rp_diff = one(r"차이 ([+-][\d.]+) pp", out)
ok(NAME("화면의 롤업 차이가 보고서와 같은 값이다"),
   pg_diff is not None and rp_diff and abs(pg_diff - float(rp_diff[0])) < 0.001,
   f"화면 {pg_diff} vs 보고서 {rp_diff[0] if rp_diff else '?'}")

# 데이터가 맞아도 **화면이 그 데이터를 안 쓰면** 소용없다. 주입된 diff 는 멀쩡한데
# 템플릿이 `R.weighted - R.even` 으로 다시 빼면 0.1 이 갈린다 — 사보타주가 그렇게 통과했다.
# 그래서 템플릿 소스에서 **반올림된 값끼리의 산술**을 금지한다.
arith = []
if os.path.exists(TPL):
    t = open(TPL, encoding="utf-8").read()
    arith = re.findall(r"R\.(?:weighted|even)\s*[-+*/]\s*R\.(?:weighted|even)", t)
ok(NAME("템플릿이 반올림된 값끼리 계산하지 않는다"), os.path.exists(TPL) and not arith,
   f"템플릿의 산술 {arith[:2]} — 차이는 export_web.py 가 원값에서 한 번만 구한다")

# README 가 "24 checks" 라고 적어 두고 실제로는 27개인 채로 지내고 있었다(UnivaBio 도 똑같았다).
# 산문에 적은 개수는 반드시 어긋난다. **권위값은 NAMES 와 SABS 이고**, README 를 거기에 묶는다.
# sabotage.py 를 **실행하지 않고** SABS 만 읽는다.
# 처음엔 모듈을 불러와서 읽었다가 포크 폭탄을 만들었다 — sabotage.py 에는 __main__ 가드가 없어서
# 불러오는 순간 사보타주 전체가 돌고, 그게 다시 이 파일을 부른다.
import ast as _ast
def _read_sabs():
    _src = open(os.path.join(ROOT, "src", "sabotage.py"), encoding="utf-8").read()
    for _n in _ast.parse(_src).body:
        if isinstance(_n, _ast.Assign) and any(getattr(_t, "id", "") == "SABS" for _t in _n.targets):
            return len(_ast.literal_eval(_n.value))
    return None
try:
    n_sabs = _read_sabs()
except Exception:
    n_sabs = None

_rd = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
_bad = []
if n_sabs is None:
    _bad.append("sabotage.py 에서 SABS 를 못 읽었다")
_mc = re.search(r"check\.py\s*#\s*(\d+)\s*checks", _rd)
_ms = re.search(r"sabotage\.py\s*#\s*break\s*(\d+)\s*things", _rd)
if not _mc:
    _bad.append("README 에 'check.py # N checks' 가 없다")
elif int(_mc.group(1)) != len(NAMES):
    _bad.append(f"README 는 검사 {_mc.group(1)}개라는데 실제 {len(NAMES)}개")
if not _ms:
    _bad.append("README 에 'sabotage.py # break N things' 가 없다")
elif n_sabs is not None and int(_ms.group(1)) != n_sabs:
    _bad.append(f"README 는 사보타주 {_ms.group(1)}개라는데 실제 {n_sabs}개")
ok(NAME("README 가 말하는 검사·사보타주 개수가 실제와 같다"), not _bad, "; ".join(_bad))

# 제출 본문도 표류한다. grid-clock 에서 devpost 가 "3 a.m." 을 여섯 군데 남긴 채 지나갔다 —
# 그때 검사가 못 잡은 이유는 (1) 정수를 안 보고 (2) "값 풀에 들어 있는가"만 봤기 때문이다.
# 그래서 여기서는 **자리마다 따로, 정수까지** 본다. 없으면 없다고 실패한다(빈 집합에 통과하지 않는다).
DEV = os.path.join(ROOT, "submission", "devpost.md")
_dp_bad = []
if not os.path.exists(DEV):
    _dp_bad.append("submission/devpost.md 가 없다")
else:
    _dv = open(DEV, encoding="utf-8").read()
    for _label, _po, _pd in (
        ("배수",        r"허용된 시간의 비: (\d+)배",                      r"\*\*(\d+)×\*\* the permitted time"),
        ("건수0 행",    r"건수 0 위에 퍼센트를 얹은 행: (\d+)개",           r"\*\*(\d+) row\*\* reports a percentage on no cases"),
        ("N/A 행",      r"'N/A/TBD' 로 적은 행: (\d+)개",                   r"\*\*(\d+) more\*\* carry a target"),
        ("고르게 평균", r"고르게 평균\(각주 방법, \d+곳\)\s+([\d.]+) %",   r"Evenly: ([\d.]+) %"),
        ("가중 평균",   r"건수로 가중.*?([\d.]+) %\s+차이",                r"reported: ([\d.]+) %"),
        ("재구성 합",   r"재구성한 건수 합 ([\d,]+) vs",                    r"sum to ([\d,]+) cases"),
        ("보고서 분모", r"재구성한 건수 합 [\d,]+ vs 보고서 ([\d,]+)",      r"against the\s+published ([\d,]+)"),
        ("잔차",        r"잔차 \+(\d+)",                                   r"A \*\*\+(\d+)\*\* residual"),
        ("시계 표현",   r"(\d+)개 기준이 서로 다른 표현",                   r"Across (\d+) first-event\s+standards"),
        ("표현 가짓수", r"서로 다른 표현 (\d+)가지",                        r"\*\*(\d+) different phrasings"),
        ("LTB 건수",    r"LTB 한 행: n=([\d,]+)",                           r"\*\*([\d,]+)\*\* cases in the\s+same report"),
    ):
        _a, _b = one(_po, out, re.S), one(_pd, _dv, re.S)
        if not _a:
            _dp_bad.append(f"{_label}: analyze 출력에서 못 읽었다")
        elif not _b:
            _dp_bad.append(f"{_label}: devpost 에서 못 읽었다")
        elif _a[0].replace(",", "") != _b[0].replace(",", ""):
            _dp_bad.append(f"{_label}: 출력 {_a[0]} vs 본문 {_b[0]}")
ok(NAME("제출 본문(devpost.md)의 수치가 출력과 일치한다"), not _dp_bad, "; ".join(_dp_bad))

# **OSETS 가 필터에 조용히 지워진 것이 이 프로젝트에서 두 번째였다.**
# 앞번은 롤업 정규식(격차가 -2.7 대신 -4.2 로 부풀었다), 이번은 export_web 이 들고 있던
# 제 사본의 `proceeds to a first` — 원문은 `the OSETs **proceed**` 라 복수형이었다.
# 터미널은 17행, 화면은 16행이었고 시계 시작점 가짓수도 12 대신 11 이었다.
# OSETS 는 목표가 짧아진 유일한 심판소, 즉 쉬운 이야기의 반례다. **필터가 반례부터 지운다.**
_LAD = None
try:
    _idx = open(IDX, encoding="utf-8").read() if os.path.exists(IDX) else ""
    _m = re.search(r"const DATA = (\{.*?\});", _idx, re.S)
    _D = json.loads(_m.group(1)) if _m else {}
    _LAD = _D.get("ladder")
except Exception as _e:
    _LAD = None
_lb = []
_a_rows = one(r"시계 시작점: (\d+)개 기준이", out)
_a_clocks = one(r"서로 다른 표현 (\d+)가지", out)
if _LAD is None:
    _lb.append("index.html 에서 사다리를 못 읽었다")
elif not (_a_rows and _a_clocks):
    _lb.append("analyze 출력에서 행 수/가짓수를 못 읽었다")
else:
    if len(_LAD) != int(_a_rows[0]):
        _lb.append(f"행 수: 분석 {_a_rows[0]} vs 화면 {len(_LAD)}")
    _pc = len({r.get("c") for r in _LAD if r.get("c")})
    if _pc != int(_a_clocks[0]):
        _lb.append(f"시계 시작점 가짓수: 분석 {_a_clocks[0]} vs 화면 {_pc}")
ok(NAME("화면 사다리가 분석과 같은 행 수·같은 시계 시작점 가짓수를 쓴다"), not _lb, "; ".join(_lb))

# 규칙이 두 벌이면 한 벌만 고쳐진다. rules.py 말고 어디서도 정의하지 못하게 한다.
import glob as _glob
_dup = []
for _f in sorted(_glob.glob(os.path.join(ROOT, "src", "*.py"))):
    _b = os.path.basename(_f)
    if _b in ("rules.py", "check.py", "sabotage.py"):
        continue
    _t = open(_f, encoding="utf-8").read()
    if re.search(r"proceeds?\s*\\?s?\+?\\?s\*to|proceeds to a first|hearings\?? scheduled within", _t):
        _dup.append(f"{_b} 가 첫 심리 규칙을 직접 적고 있다")
ok(NAME("첫 심리 판정 규칙이 한 벌이다(제 사본을 둔 파일이 없다)"), not _dup, "; ".join(_dup[:3]))

# **README 만 묶으면 나머지가 샌다.** 제출 본문·AI 고지·체크리스트가 전부 옛 수를 들고 있었고,
# 심사위원이 읽는 건 그쪽이다. 개수를 적은 문서를 **전부** 훑어 코드와 대조한다.
import glob as _g9
_cnt_bad = []
_docs9 = ([os.path.join(ROOT, f) for f in ("README.md", "VERIFICATION.md")]
          + sorted(_g9.glob(os.path.join(ROOT, "submission", "*.md")))
          + sorted(_g9.glob(os.path.join(ROOT, "submission", "*.html"))))
_N_CHK, _N_SAB = len(NAMES), n_sabs
_pats9 = [
    (r"(\d+)\s*checks?,? (?:at a|whose|on the|run on)", _N_CHK, "검사"),
    (r"check\.py[^\n]*?#\s*(\d+)\s*checks", _N_CHK, "검사"),
    (r"check\.py[^\n]*?(\d+)\s*checks", _N_CHK, "검사"),
    (r"`check\.py` \((\d+) checks\)", _N_CHK, "검사"),
    (r"→ \*\*(\d+)/\d+\*\*", _N_CHK, "검사"),
    (r"(\d+) checks at a fixed denominator", _N_CHK, "검사"),
    (r"(\d+)\s*(?:planted|deliberate) defects", _N_SAB, "사보타주"),
    (r"breaks? (\d+) things", _N_SAB, "사보타주"),
    (r"break (\d+) things", _N_SAB, "사보타주"),
    (r"Current: (\d+) of \d+ caught", _N_SAB, "사보타주"),
    (r"\*\*(\d+)/\d+ 검출", _N_SAB, "사보타주"),
]
for _f9 in _docs9:
    if not os.path.exists(_f9):
        continue
    _t9 = open(_f9, encoding="utf-8").read()
    for _p9, _w9, _k9 in _pats9:
        if _w9 is None:
            continue
        for _m9 in re.finditer(_p9, _t9):
            if int(_m9.group(1)) != _w9:
                _cnt_bad.append(f"{os.path.basename(_f9)}: {_k9} {_m9.group(1)} (실제 {_w9})")
_cnt_bad = sorted(set(_cnt_bad))
ok(NAME("어느 문서도 검사·사보타주 개수를 틀리게 적지 않았다"), not _cnt_bad, "; ".join(_cnt_bad[:4]))

# **화면의 롤업 수치를 아무도 안 보고 있었다.** `export_web.py` 안에서 `tot` 이라는 이름이
# 두 번 쓰여, 재구성 건수 합(17,707)이 드리프트 루프의 **일수 합(210)** 으로 덮여 있었다.
# 페이지는 "재구성 210건"을 싣고 README 는 17,707 을 말하는 상태로 검사 31개가 전부 초록이었다.
_rb = []
try:
    _idx2 = open(IDX, encoding="utf-8").read() if os.path.exists(IDX) else ""
    _m2 = re.search(r"const DATA = (\{.*?\});", _idx2, re.S)
    _R2 = (json.loads(_m2.group(1)).get("rollup") or {}) if _m2 else {}
except Exception as _e:
    _R2 = {}; _rb.append(f"index.html 에서 롤업을 못 읽었다: {_e}")
for _label, _pat, _key, _tol in (
    ("보고 퍼센트", r"보고서: ([\d.]+) %", "reported_pct", 0.05),
    ("보고 분모",   r"보고서: [\d.]+ %\s*\(n=([\d,]+)\)", "reported_n", 0.5),
    ("고르게 평균", r"고르게 평균\(각주 방법, \d+곳\)\s+([\d.]+) %", "even", 0.05),
    ("가중 평균",   r"건수로 가중.*?([\d.]+) %\s+차이", "weighted", 0.05),
    ("재구성 합",   r"재구성한 건수 합 ([\d,]+) vs", "reconstructed_n", 0.5),
):
    _a2 = one(_pat, out, re.S)
    if not _a2:
        _rb.append(f"{_label}: analyze 출력에서 못 읽었다"); continue
    _want = float(_a2[0].replace(",", ""))
    _got = _R2.get(_key)
    if _got is None:
        _rb.append(f"{_label}: 화면에 {_key} 가 없다")
    elif abs(float(_got) - _want) > _tol:
        _rb.append(f"{_label}: 출력 {_want:g} vs 화면 {float(_got):g}")
ok(NAME("화면의 롤업 수치가 analyze 출력과 전부 일치한다"), not _rb, "; ".join(_rb[:3]))

# **그림이 아래에서 잘려 헤드라인 행이 빠져 있었다.** 사다리를 17행에서 20행으로 늘렸는데
# 스크린샷 높이가 900px 에 박혀 있어, 영상이 "허용된 시간 순으로 전부"라고 말하는 동안
# 화면에는 240일 행(이 프로젝트의 헤드라인)이 없었다. 행 수에 맞는 높이인지 본다.
_fb = []
_lad_png = os.path.join(ROOT, "figures", "01-ladder.png")
if not os.path.exists(_lad_png):
    _fb.append("figures/01-ladder.png 이 없다 — python3 src/shots.py")
else:
    import struct as _st
    with open(_lad_png, "rb") as _f:
        _hdr = _f.read(32)
    _w, _h = _st.unpack(">II", _hdr[16:24])
    _n_rows = len(_LAD) if _LAD else 0
    _need = _n_rows * 28 + 60          # 행당 최소 28px + 머리말·여백
    if _n_rows == 0:
        _fb.append("사다리 행 수를 못 읽었다")
    elif _h < _need:
        _fb.append(f"그림 높이 {_h}px 인데 {_n_rows}행이면 최소 {_need}px 필요 — 아래가 잘렸다")
    else:
        # **PNG 만 보면 안 된다.** 사보타주로 shots.py 의 높이를 되돌려도 그림을 다시 찍지
        # 않으니 검사가 초록이었다("놓침"). 찍는 쪽 여유도 같이 본다 —
        # `TALL` 은 넉넉히 찍고 여백을 잘라내는 설계라 **한 번도 걸리면 안 되는 값**이다.
        _sh = open(os.path.join(ROOT, "src", "shots.py"), encoding="utf-8").read()
        _mt = re.search(r"^TALL\s*=\s*(\d+)", _sh, re.M)
        if not _mt:
            _fb.append("shots.py 에서 TALL 을 못 읽었다")
        elif int(_mt.group(1)) < _need * 3:
            _fb.append(f"shots.py 의 TALL={_mt.group(1)} 이 {_n_rows}행에 비해 빠듯하다 "
                       f"(여백 잘라내기 설계라 {_need * 3}px 이상이어야 한다)")
ok(NAME("사다리 그림이 모든 행을 담고 있다(아래가 잘리지 않았다)"), not _fb, "; ".join(_fb))

print()
failed = 0
for n in NAMES:
    g_, d_ = result[n]
    failed += not g_
    print(f"  {'OK ' if g_ else 'BAD'}  {n}" + ("" if g_ else f"   {d_}"))
print(f"\n{len(NAMES) - failed}/{len(NAMES)} 통과. (분모 고정 — 실패해도 개수가 줄지 않는다)")
sys.exit(1 if failed else 0)
