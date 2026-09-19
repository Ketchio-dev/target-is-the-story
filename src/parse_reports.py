"""연차보고서의 KPI 표를 뜯는다. **수를 손으로 옮기지 않기 위한 다리.**

    python3 src/parse_reports.py

표는 접근성 마크업이 잘 되어 있어 정규식으로 안전하게 읽힌다:
  <th id="sbtr11" scope="row">기준 문장</th>
  <td headers="th-year-sbt sbtr11">80%</td>        <- 목표
  <td headers="th-sbtfy-n sbtr11">7,735</td>       <- 그 해 건수
  <td headers="th-sbtfy-p sbtr11">100%</td>        <- 그 해 달성률
`headers` 속성이 어느 tribunal 인지까지 알려 준다. **행 id 로 묶기 때문에 열이
밀려도 값이 어긋나지 않는다** — 위치로 읽으면 표가 한 칸만 바뀌어도 조용히 틀린다.
"""
import html, json, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import ROOT, SOURCES, provenance, text

ROW = re.compile(r'<th id="([a-z0-9]+?)"[^>]*scope="row"[^>]*>(.*?)</th>(.*?)</tr>', re.S | re.I)
CELL = re.compile(r'<td headers="([^"]*?)"[^>]*>(.*?)</td>', re.S | re.I)


def clean(s):
    s = re.sub(r"<abbr[^>]*>(.*?)</abbr>", r"\1", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def num(s):
    s = clean(s).replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


# "within 240 days", "within 24 hours", "within five business days"
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 10 - 1, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30}


DUR_AT = re.compile(r"within\s+([\w,]+)\s+(calendar days|business days|days|hours|months)", re.I)


def permitted_days(std):
    m = DUR_AT.search(std)
    if not m:
        return None, ""
    raw, unit = m.group(1).replace(",", "").lower(), m.group(2).lower()
    n = WORDS.get(raw)
    if n is None:
        try:
            n = float(raw)
        except ValueError:
            return None, ""
    # 영업일은 달력일이 아니다. 환산하지 않고 **환산했다는 사실을 들고 다닌다.**
    raw_label = f"{m.group(1)} {unit}"
    if unit == "hours":
        return n / 24.0, raw_label
    if unit == "business days":
        return n * 7.0 / 5.0, raw_label
    if unit == "months":
        return n * 30.0, raw_label
    return float(n), raw_label


def clock_start(std):
    """언제부터 세기 시작하는가. **기간 표현 뒤에 오는 절**을 잡는다.

    앞에서부터 첫 `from|after|of` 를 잡으면 안 된다 — 기준 문장이 거의 전부
    "Percentage **of** hearings scheduled…" 로 시작해서 **모든 행이 같은 쓰레기**를
    들고 다녔다. 시계 시작점은 이 분석 주장의 절반이라, 조용히 틀리면 제품이 틀린다.
    """
    m = DUR_AT.search(std)
    if not m:
        # 기간 표현이 없으면 **시계 시작점도 없다.** 문장 앞머리를 잡으면
        # "case lifecycle" 행 32개가 전부 'of cases within the case…' 라는 같은
        # 쓰레기를 들고 다닌다. 없는 것은 없다고 둔다.
        return ""
    tail = std[m.end():]
    c = re.search(r"\b(from|after|following|of)\s+(the\s+)?([^,.;]{4,70})", tail, re.I)
    return c.group(0).strip() if c else ""


def parse(name):
    body = text(name)
    out = []
    for rid, th, rest in ROW.findall(body):
        std = clean(th)
        if not std or "%" in std[:3]:
            continue
        cells = {}
        for hdr, val in CELL.findall(rest):
            for h in hdr.split():
                if h != rid:
                    cells[h] = clean(val)
        # **보고서마다 헤더 이름이 다르다.** 2024-25 는 `th-sbtfy-n`, 그 전 해들은 `sbtfyn`.
        # 한 판만 다루면 옛 보고서가 조용히 0행이 된다 — 실제로 그랬고, "3년 추세"가
        # 사라진 줄도 모를 뻔했다. 두 판을 모두 받되 **어느 쪽으로 읽었는지 기록한다.**
        pick = lambda *pats: next((v for h, v in cells.items()
                                   if any(re.fullmatch(p_, h) for p_ in pats)), None)
        fy_n = pick(r"th-\w*fy-n", r"\w*fyn")
        fy_p = pick(r"th-\w*fy-p", r"\w*fyp")
        target = pick(r"th-year-\w+", r"\w*target")
        trib = None
        for h in cells:
            m = re.fullmatch(r"th-year-([a-z]+)", h)
            if m:
                trib = m.group(1)
        if not trib:
            trib = re.sub(r"r?\d+$", "", rid) or rid
        if target is None or fy_p is None:
            continue
        days, unit = permitted_days(std)
        out.append({
            "row_id": rid, "tribunal": (trib or rid[:3]).upper(), "standard": std,
            "target_pct": num(target), "fy_n": num(fy_n), "fy_pct": num(fy_p),
            "permitted_days": days, "permitted_as_written": unit,
            # **"N/A" 는 0 이 아니다.** `num()` 이 둘 다 None 을 주는 바람에
            # `(None or 0) == 0` 으로 뭉개졌고, "9개 행이 건수 0 위에 퍼센트를 얹었다"고
            # 적었다. 실제로는 진짜 0 이 1건, 보고를 안 한 것(N/A·TBD)이 8건이다.
            # **보고를 안 한 것을 0 이라고 부르는 것은 우리가 지적하려던 바로 그 잘못이다.**
            "fy_n_raw": clean(fy_n) if fy_n is not None else "",
            "fy_pct_raw": clean(fy_p) if fy_p is not None else "",
            "zero_denominator": num(fy_n) == 0,
            "not_reported": num(fy_n) is None, "clock_start": clock_start(std),
            "source": name,
        })
    return out


def main():
    all_rows, per_report = [], {}
    for name in ("ar_2024_25", "ar_2023_24", "ar_2022_23"):
        try:
            rows = parse(name)
        except Exception as e:                       # 없는 해가 있어도 나머지는 만든다
            print(f"  ! {name} 파싱 실패: {e}")
            continue
        per_report[name] = len(rows)
        all_rows += rows
    foot = ""
    m = re.search(r"evenly weighted average[^<]{0,220}", text("ar_2024_25"))
    if m:
        foot = clean(m.group(0))
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump({"rows": all_rows, "rollup_footnote": foot, "provenance": provenance()},
              open(os.path.join(ROOT, "data", "kpi.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for name, n in per_report.items():
        print(f"  {name}: KPI 행 {n}개")
    if not all_rows:
        # **0행으로 끝내면서 성공을 보고하지 않는다.** 아래 모든 검사가 빈 집합 위에서
        # 참이 되고, "파서가 죽었다"와 "데이터가 멀쩡하다"가 구분되지 않는다.
        raise SystemExit("KPI 행을 한 개도 못 읽었다 — 헤더 형식이 바뀌었는지 본다")
    print(f"  전체 {len(all_rows)}행 · tribunal {len({r['tribunal'] for r in all_rows})}곳")
    print(f"  롤업 각주: {foot[:120] or '(못 찾음)'}")


if __name__ == "__main__":
    main()
