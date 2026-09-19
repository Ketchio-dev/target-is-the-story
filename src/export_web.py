"""화면용 축약 데이터 + 템플릿 주입.

`web/page.html` 은 템플릿이고 **수치가 하나도 없다.** 이 스크립트가 주입해 index.html 을
만든다. fetch 는 file:// 에서 막히므로 주입이어야 하고, 그래야 클론 후 더블클릭으로 열린다.
"""
import json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
OPEN, CLOSE = "/*DATA_START*/", "/*DATA_END*/"
FULL = {"CRB": "Custody Review Board", "ACRB": "Animal Care Review Board",
        "CFSRB": "Child and Family Services Review Board", "FSC": "Fire Safety Commission",
        "LAT": "Licence Appeal Tribunal", "LTB": "Landlord and Tenant Board",
        "OSETS": "Ontario Special Education Tribunals", "SBT": "Social Benefits Tribunal",
        "HRTO": "Human Rights Tribunal of Ontario", "OCPC": "Ontario Civilian Police Commission",
        "ARB": "Assessment Review Board", "OPB": "Ontario Parole Board",
        "TO": "Tribunals Ontario (roll-up)"}
from rules import is_first_hearing  # **제 사본을 두지 않는다** — rules.py 참고


def main():
    K = json.load(open(os.path.join(ROOT, "data", "kpi.json"), encoding="utf-8"))
    S = json.load(open(os.path.join(ROOT, "data", "standards.json"), encoding="utf-8"))
    rows = K["rows"]
    cur = [r for r in rows if r["source"] == "ar_2024_25"]

    ladder = sorted([r for r in cur if r["permitted_days"] and is_first_hearing(r["standard"])],
                    key=lambda r: r["permitted_days"])
    roll = [r for r in cur if "Tribunals Ontario meets" in r["standard"]]
    # analyze.py 와 **같은 정규식**이어야 한다. 좁은 쪽을 남겨 두면 화면과 보고서가 갈린다
    # — 실제로 갈렸고(−4.2 vs −2.7), 검사가 그걸 잡았다.
    COMP = re.compile(r"proceeds?\s+to\s+a\s+first\s+(held\s+hearing\s+event"
                      r"|held\s+pre-hearing\s+event|telephone\s+review|pre-hearing)", re.I)
    comp = [r for r in cur if COMP.search(r["standard"]) and r["fy_pct"] is not None]
    by_trib = defaultdict(list)
    for r in comp:
        by_trib[r["tribunal"]].append(r)
    even = sum(sum(x["fy_pct"] for x in v) / len(v) for v in by_trib.values()) / max(len(by_trib), 1)
    tot = sum(r["fy_n"] or 0 for r in comp)
    weighted = (sum((r["fy_n"] or 0) * r["fy_pct"] for r in comp) / tot) if tot else 0
    reported = next((r for r in roll if "time to proceed" in r["standard"]), None)

    trend = defaultdict(dict)
    for r in rows:
        if r["fy_pct"] is None or not r["fy_n"]:
            continue
        trend[r["tribunal"]].setdefault(r["source"], []).append(
            {"s": r["standard"], "p": r["fy_pct"], "n": r["fy_n"], "t": r["target_pct"]})

    # 드리프트를 payload 에 넣는다. 시계 시작점이 바뀌었는지까지 함께 —
    # README 가 "페이지가 그렇게 말한다"고 적어 두고 페이지는 말하지 않고 있었다.
    def clock_of(sentence):
        m = re.search(r"\b(from|after|of)\s+(the\s+)?[^,.;]{4,70}", sentence)
        return m.group(0).strip() if m else ""

    def head6(t):
        return " ".join(re.sub(r"\W+", " ", (t or "").lower()).split()[:6])

    drift = []
    old_by = defaultdict(list)
    for r in S["rows"]:
        old_by[r["tribunal"]].append(r)
    FIRSTD = re.compile(r"(first hearing|hearings?\s+(?:will\s+be\s+)?scheduled"
                        r"|scheduled\s+for\s+(?:mediation\s+or\s+)?an?\s+(?:pre-)?hearing"
                        r"|proceeds?\s+to\s+a\s+first|sets\s+a\s+hearing\s+date)", re.I)
    for t, olds in old_by.items():
        rel = [r for r in olds if FIRSTD.search(r["sentence"])]
        now = max((r for r in ladder if r["tribunal"] == t),
                  key=lambda r: r["permitted_days"], default=None)
        if not rel or not now:
            continue
        per_year = {}
        for r in rel:
            # **`tot` 이라 부르면 안 된다.** 위에서 재구성 건수 합이 `tot` 이고,
            # 이 루프가 그걸 덮어써서 페이지가 "210일"을 "재구성 건수"로 싣고 있었다.
            days_sum = sum(d["days"] for d in r["durations"] if d["days"])
            y = r["source"].replace("std_", "")
            if y not in per_year or days_sum > per_year[y]["days"]:
                per_year[y] = {"days": days_sum, "sentence": r["sentence"],
                               "clock": clock_of(r["sentence"])}
        base = max(v["days"] for v in per_year.values())
        src = max(per_year.values(), key=lambda v: v["days"])
        drift.append({
            "t": t, "then": per_year, "then_days": base, "now_days": now["permitted_days"],
            "now_s": now["standard"], "now_pct": now["fy_pct"], "now_n": now["fy_n"],
            "delta": round(now["permitted_days"] - base, 1),
            "clock_changed": bool(src["clock"] and now["clock_start"]
                                  and head6(src["clock"]) != head6(now["clock_start"])),
            "then_clock": src["clock"], "now_clock": now["clock_start"],
        })
    drift.sort(key=lambda d: d["t"])

    payload = {
        "drift": drift,
        "full_names": FULL,
        "ladder": [{"t": r["tribunal"], "d": r["permitted_days"], "w": r["permitted_as_written"],
                    "c": r["clock_start"], "target": r["target_pct"], "pct": r["fy_pct"],
                    "n": r["fy_n"], "s": r["standard"], "zero": r["zero_denominator"], "nr": r["not_reported"],
                    "raw": r["fy_pct_raw"]}
                   for r in ladder],
        # **0 과 "보고 안 함"을 갈라 싣는다.** 합쳐서 세면 우리가 지적하려던 잘못을 우리가 한다.
        "zero_rows": [{"t": r["tribunal"], "s": r["standard"], "raw": r["fy_pct_raw"]}
                      for r in cur if r["zero_denominator"] and r["target_pct"] is not None],
        "not_reported_rows": [{"t": r["tribunal"], "s": r["standard"], "raw": r["fy_pct_raw"]}
                              for r in cur if r["not_reported"] and r["target_pct"] is not None],
        "rollup": {
            "reported_pct": reported["fy_pct"] if reported else None,
            "reported_n": reported["fy_n"] if reported else None,
            "footnote": K["rollup_footnote"],
            "even": round(even, 1), "weighted": round(weighted, 1),
            # **반올림한 값끼리 빼지 않는다.** 89.2 − 93.3 = −4.1 이지만 원값 차는 −4.2 다.
            # 페이지와 보고서가 0.1 로 갈렸던 자리 — 차이는 한 곳에서만 계산한다.
            "diff": round(weighted - even, 1),
            "reconstructed_n": tot,
            "components": [{"t": r["tribunal"], "p": r["fy_pct"], "n": r["fy_n"],
                            "s": r["standard"]} for r in comp],
            "all_rollups": [{"s": r["standard"], "p": r["fy_pct"], "n": r["fy_n"]} for r in roll],
        },
        "standards_old": S["rows"],
        "trend": trend,
        "provenance": {**K["provenance"], **S["provenance"]},
        # 우리를 죽이는 문장들. **화면 안에 둔다.**
        "against": {
            "nothing_new": "Every number here is published by Tribunals "
                           "Ontario itself, and the averaging method is their own footnote in the "
                           "same table. What we did is sort it and recompute it.",
            "not_slow": "A longer permitted time does not mean a tribunal is slower or worse. "
                        "A custody review and a disability-income appeal are not the same case.",
            "converted": "Business days and months were converted to calendar days. Every row "
                         "also carries the wording exactly as published, because the conversion "
                         "is ours and the wording is theirs.",
            "not_advice": "This is not legal advice and tells nobody what to do in their matter. "
                          "It describes how a published percentage is built.",
            "sjto_only": "The 2012 and 2013 standards cover the seven-tribunal SJTO cluster only, "
                         "not all thirteen. The drift panel says which tribunals it can and cannot "
                         "compare.",
        },
    }
    os.makedirs(WEB, exist_ok=True)
    json.dump(payload, open(os.path.join(WEB, "data.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    tpl_path = os.path.join(WEB, "page.html")
    if not os.path.exists(tpl_path):
        print(f"  web/data.json 작성 (사다리 {len(ladder)}행). 템플릿이 없어 index.html 은 건너뛴다")
        return
    tpl = open(tpl_path, encoding="utf-8").read()
    if OPEN not in tpl or CLOSE not in tpl:
        raise SystemExit(f"템플릿에 {OPEN} … {CLOSE} 표시가 없다")
    head, rest = tpl.split(OPEN, 1)
    _o, tail = rest.split(CLOSE, 1)
    out = head + OPEN + "\nconst DATA = " + json.dumps(payload, ensure_ascii=False,
                                                       separators=(",", ":")) + ";\n" + CLOSE + tail
    open(os.path.join(WEB, "index.html"), "w", encoding="utf-8").write(out)
    kb = os.path.getsize(os.path.join(WEB, "index.html")) // 1024
    print(f"  web/data.json + web/index.html 작성 (사다리 {len(ladder)}행 · {kb} KB)")


if __name__ == "__main__":
    main()
