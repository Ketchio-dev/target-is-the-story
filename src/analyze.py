"""수치를 찍는다. **문서·화면이 인용할 수 있는 유일한 출처.**

    python3 src/analyze.py

여기서 새로 계산하는 것은 **롤업 재계산 하나뿐**이고, 그것도 보고서가 자기 각주에서
방법을 밝힌 것을 그대로 따라 한 것이다. 나머지는 전부 보고서 표를 옮겨 온 것이다.
우리가 '발견'한 것은 없다 — **배열이 다를 뿐이다.** 그 문장을 화면 맨 위에 둔다.
"""
import json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ROOT, "data", "kpi.json"), encoding="utf-8"))
ROWS = D["rows"]
CUR = "ar_2024_25"

# "초기 심리까지 걸리는 시간" 계열. 롤업이 이 계열을 tribunal 별로 평균낸다.
# **동사 일치 하나로 한 tribunal 이 통째로 빠졌다.** OSETs 행은 "the OSETs **proceed**
# to a first held **pre-hearing** event" 라서 `proceeds` 에도, `held hearing event` 에도
# 안 걸렸다. 각주가 말하는 "reporting on that" 에 해당하는 행인데 조용히 빠져 있었고,
# 그만큼 롤업 격차가 부풀었다.
from rules import FIRST_EVENT, SCHEDULED, is_first_hearing  # 규칙 한 벌 — rules.py 참고


def cur(pred):
    return [r for r in ROWS if r["source"] == CUR and pred(r)]


print("\n  === 1. 같은 100 % 가 24시간과 240일을 뜻한다 ===")
ladder = [r for r in cur(lambda r: is_first_hearing(r["standard"]))
          if r["permitted_days"]]
ladder.sort(key=lambda r: r["permitted_days"])
print(f"  {'허용':>8} {'원문 표현':<20} {'목표':>5} {'달성':>5} {'건수':>9}  tribunal")
for r in ladder:
    flag = ("   ← 건수 0에 붙은 퍼센트" if r["zero_denominator"]
                else "   ← 결과 미보고(" + r["fy_pct_raw"] + ")" if r["not_reported"] else "")
    pctv = "N/A" if r["fy_pct"] is None else f"{r['fy_pct']:.0f}"
    print(f"  {r['permitted_days']:7.1f}일 {r['permitted_as_written']:<20} "
          f"{(r['target_pct'] or 0):5.0f} {pctv:>5} {(r['fy_n'] or 0):9,.0f}  {r['tribunal']}{flag}")
fast = min((r for r in ladder if r["fy_pct"] == 100), key=lambda r: r["permitted_days"])
slow = max((r for r in ladder if r["fy_pct"] == 100), key=lambda r: r["permitted_days"])
print(f"\n  둘 다 100 % 달성: {fast['tribunal']} {fast['permitted_as_written']} (n={fast['fy_n']:,.0f})"
      f"  vs  {slow['tribunal']} {slow['permitted_as_written']} (n={slow['fy_n']:,.0f})")
print(f"  허용된 시간의 비: {slow['permitted_days'] / fast['permitted_days']:.0f}배."
      f" 달성률의 차: 0 pp.")
print(f"  → **퍼센트는 기다린 시간이 아니라 목표를 맞췄는지를 잰다.**")

clocks = {r["clock_start"] for r in ladder if r["clock_start"]}
print(f"\n  시계 시작점: {len(ladder)}개 기준이 서로 다른 표현 {len(clocks)}가지로 시작점을 적는다")
for c in sorted(clocks):
    who = sorted({r["tribunal"] for r in ladder if r["clock_start"] == c})
    print(f"    {', '.join(who):<22} {c}")
print("  → 같은 퍼센트가 서로 다른 날부터 세고 있다.")

print("\n  === 2. 목표는 붙어 있는데 결과가 없는 행 ===")
zero = cur(lambda r: r["zero_denominator"] and r["target_pct"] is not None)
notrep = cur(lambda r: r["not_reported"] and r["target_pct"] is not None)
print(f"  건수 0 위에 퍼센트를 얹은 행: {len(zero)}개")
for r in zero:
    print(f"    {r['tribunal']:<6} {r['fy_n_raw']}건 / {r['fy_pct_raw']} | {r['standard'][:70]}")
print(f"  목표는 있는데 결과를 '{'/'.join(sorted({r['fy_pct_raw'] for r in notrep}))}' 로 적은 행: {len(notrep)}개")
for r in notrep:
    print(f"    {r['tribunal']:<6} {r['fy_pct_raw']:<5} | {r['standard'][:70]}")
print(f"  → **둘은 다르다.** N/A 는 보고하지 않겠다는 뜻이고, 0 % of 0 은 퍼센트가 아니다.")
print(f"     앞 판본은 둘을 합쳐 9개라고 적었다 — 보고 안 한 것을 0 이라 부르는 것은")
print(f"     우리가 지적하려던 바로 그 잘못이다.")

print("\n  === 3. 92 % 는 무엇의 평균인가 ===")
roll = next((r for r in cur(lambda r: "time to proceed to the initial hearing event" in r["standard"]) ), None)
comp = [r for r in cur(lambda r: FIRST_EVENT.search(r["standard"])) if r["fy_pct"] is not None]
if roll:
    print(f"  보고서: {roll['fy_pct']:.0f} %  (n={roll['fy_n']:,.0f})")
    print(f"  각주 원문: “{D['rollup_footnote']}”")
    # 각주가 밝힌 방법 그대로: tribunal 별로 고르게 평균
    by_trib = defaultdict(list)
    for r in comp:
        by_trib[r["tribunal"]].append(r)
    even = sum(sum(x["fy_pct"] for x in v) / len(v) for v in by_trib.values()) / len(by_trib)
    tot_n = sum(r["fy_n"] or 0 for r in comp)
    weighted = (sum((r["fy_n"] or 0) * r["fy_pct"] for r in comp) / tot_n) if tot_n else 0
    print(f"\n  고르게 평균(각주 방법, {len(by_trib)}곳)      {even:5.1f} %")
    print(f"  건수로 가중(같은 행, 같은 수)              {weighted:5.1f} %   차이 {weighted - even:+.1f} pp")
    print(f"  우리가 재구성한 건수 합 {tot_n:,.0f} vs 보고서 {roll['fy_n']:,.0f}"
          f"   (잔차 {tot_n - roll['fy_n']:+,.0f} — 어느 행이 들어가는지 보고서가 밝히지 않는다)")
    # 가장 바쁜 tribunal 이 이 계열을 아예 보고하지 않는다
    ltb = [r for r in cur(lambda r: r["tribunal"] == "LTB" and r["fy_n"] and r["fy_n"] > 1000
                                and r["fy_pct"] is not None)]
    if ltb:
        big = max(ltb, key=lambda r: r["fy_n"])
        print(f"\n  같은 해 LTB 한 행: n={big['fy_n']:,.0f}, 달성 {big['fy_pct']:.0f} %"
              f" — 롤업 분모({roll['fy_n']:,.0f})의 {big['fy_n'] / roll['fy_n']:.1f}배다.")
        print(f"    “{big['standard'][:92]}”")
        print(f"  LTB 는 위 계열을 **보고하지 않는다.** 그래서 92 % 는 가장 바쁜 곳을 뺀 평균이다.")

print("\n  === 4. 좋은 수와 나쁜 수의 분모가 다르다 (같은 tribunal, 같은 보고서) ===")
for t in ("HRTO", "LTB", "SBT", "LAT"):
    rs = [r for r in cur(lambda r: r["tribunal"] == t and r["fy_n"] and r["fy_pct"] is not None)]
    if len(rs) < 2:
        continue
    hi = max(rs, key=lambda r: r["fy_pct"])
    lo = min(rs, key=lambda r: r["fy_pct"])
    if hi["fy_pct"] == lo["fy_pct"]:
        continue
    ratio = max(hi["fy_n"], lo["fy_n"]) / max(min(hi["fy_n"], lo["fy_n"]), 1)
    print(f"  {t}: 가장 높은 {hi['fy_pct']:.0f} % (n={hi['fy_n']:,.0f})  vs  "
          f"가장 낮은 {lo['fy_pct']:.0f} % (n={lo['fy_n']:,.0f})   분모 차 {ratio:.0f}배")

print("\n  === 5. 13년 전 같은 tribunal 의 같은 기준 ===")
SP = os.path.join(ROOT, "data", "standards.json")
if not os.path.exists(SP):
    print("  data/standards.json 이 없다 — python3 src/parse_standards.py")
else:
    S = json.load(open(SP, encoding="utf-8"))["rows"]
    # **인접성을 요구하면 반례가 조용히 사라진다.** "hearings **will be** scheduled"(CFSRB
    # 2013 전부)와 "scheduled for **mediation or** a hearing"(OSETS)이 안 잡혔다.
    # 그 결과 CFSRB 는 "2013 없음"이 되어 +40일 늘어난 것처럼 보였고(실제로는 그대로),
    # **목표가 짧아진 유일한 곳인 OSETS 는 표에서 통째로 빠졌다.**
    # 필터가 우리 이야기에 불리한 자료를 지우는 것 — 이게 가장 나쁜 종류의 버그다.
    FIRST = re.compile(
        r"(first hearing|hearings?\s+(?:will\s+be\s+)?scheduled"
        r"|scheduled\s+for\s+(?:mediation\s+or\s+)?an?\s+(?:pre-)?hearing"
        r"|proceeds?\s+to\s+a\s+first|sets\s+a\s+hearing\s+date)", re.I)
    cur_first = {}
    for r in cur(lambda r: FIRST.search(r["standard"]) and r["permitted_days"]):
        prev = cur_first.get(r["tribunal"])
        # 한 tribunal 이 여러 행을 내면 **가장 긴 것**을 쓴다. 짧은 것만 고르면
        # 우리에게 유리한 쪽을 고르는 것이 된다.
        if not prev or r["permitted_days"] > prev["permitted_days"]:
            cur_first[r["tribunal"]] = r
    old_first = {}
    for r in S:
        if not FIRST.search(r["sentence"]):
            continue
        tot = sum(d["days"] for d in r["durations"] if d["days"])
        k = (r["tribunal"], r["source"])
        if k not in old_first or tot > old_first[k]["days"]:
            old_first[k] = {"days": tot, "row": r}
    print(f"  {'tribunal':<7} {'2012':>8} {'2013':>8} {'2024-25':>9}   변화")
    moved, same = [], []
    for t in sorted(cur_first):
        a = old_first.get((t, "std_2012"))
        b = old_first.get((t, "std_2013"))
        c = cur_first[t]
        if not (a or b):
            continue
        # README 가 "the longest first-hearing standard" 라고 말한다. 2012 를 우선하면
        # 2013 에 더 긴 기준이 있을 때 문서와 코드가 다른 말을 한다.
        base = max(x["days"] for x in (a, b) if x)
        d = c["permitted_days"] - base
        tag = "그대로" if abs(d) < 0.5 else f"{d:+.0f}일"
        (same if abs(d) < 0.5 else moved).append(t)
        # **시계 시작점이 바뀌면 날짜 수를 나란히 놓을 수 없다.** 40일 늘어 보여도
        # "접수일부터"가 "적격 판정일부터"로 바뀐 것이면 다른 구간을 재는 것이다.
        oc = re.search(r"\b(after|from|of)\s+(the\s+)?[^,.;]{4,50}", (a or b)["row"]["sentence"])
        nc = c["clock_start"]
        drift_note = ""
        if oc and nc:
            # 문장 길이가 달라 잘리는 위치가 다르다. **앞 여섯 낱말**로 견준다 —
            # 전체 문자열을 비교하면 HRTO 처럼 한 글자 차이로 "바뀌었다"가 찍힌다.
            k1 = " ".join(re.sub(r"\W+", " ", oc.group(0).lower()).split()[:6])
            k2 = " ".join(re.sub(r"\W+", " ", nc.lower()).split()[:6])
            if k1 != k2:
                drift_note = "  ← 시계 시작점도 바뀌었다(직접 비교 불가)"
        print(f"  {t:<7} {a['days'] if a else float('nan'):8.0f} {b['days'] if b else float('nan'):8.0f} "
              f"{c['permitted_days']:9.0f}   {tag}{drift_note}")
    print(f"\n  움직인 곳 {moved} · 13년째 같은 곳 {same}")
    print(f"  → **일부만 움직였다.** 전부 움직였다면 정책 변화지만, 일부만이면 각각의 결정이다.")
    for t in moved[:2]:
        a = old_first.get((t, "std_2012")) or old_first.get((t, "std_2013"))
        print(f"\n  {t} 2012/2013: “{a['row']['sentence'][:150]}”")
        print(f"  {t} 2024-25  : “{cur_first[t]['standard'][:150]}”")
        print(f"      그 해 달성 {cur_first[t]['fy_pct']:.0f} % (n={cur_first[t]['fy_n']:,.0f})")

print("\n  === 이 분석이 말하지 않는 것 ===")
print("  · 우리는 아무것도 발굴하지 않았다. 위 수는 전부 Tribunals Ontario 가 스스로 낸 것이고,")
print("    평균 방법도 같은 표의 자기 각주다. 우리가 한 것은 **정렬과 재계산**이다.")
print("  · 허용 기간이 길다고 그 tribunal 이 일을 못한다는 뜻이 아니다. 사건 종류가 다르다.")
print("  · 영업일·개월을 달력일로 환산했다. 원문 표현을 같이 들고 다니는 이유다.")
print("  · 2012/2013 기준은 SJTO 7곳만 다룬다. 13곳 전부가 아니다 — 비교표가 그렇게 말한다.")
print("  · 이것은 법률 조언이 아니다. 누구에게도 무엇을 하라고 말하지 않는다.")

pv = D["provenance"]
print("\n  === 출처 ===")
for n, s in pv.items():
    print(f"    {n:<12} {s['bytes']:>8,} B · 받음 {s['fetched_at']} · Last-Modified {s['last_modified'] or '—'}")
