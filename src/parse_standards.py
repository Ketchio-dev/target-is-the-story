"""2012·2013 서비스 기준을 tribunal 별로 뜯는다. **목표가 움직였는지는 이게 있어야 말할 수 있다.**

    python3 src/parse_standards.py

문서는 `<h3>` 로 tribunal 이 나뉘고 그 아래 문장에 기간이 적혀 있다.
문장을 **그대로** 보관한다 — 기간만 뽑아 두면 "무엇으로부터 며칠인지"가 사라지고,
그 시계 시작점이 이 프로젝트의 절반이다.
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources import ROOT, provenance, text

WORDS = {"four": 4, "five": 5, "seven": 7, "ten": 10, "fourteen": 14, "twenty": 20,
         "twenty-five": 25, "thirty": 30, "sixty": 60, "ninety": 90}
NAMES = {
    "Child and Family Services Review Board": "CFSRB",
    "Custody Review Board": "CRB",
    "Human Rights Tribunal of Ontario": "HRTO",
    "Landlord and Tenant Board": "LTB",
    "Ontario Special Education Tribunals (English and French)": "OSETS",
    "Social Benefits Tribunal": "SBT",
}
# `within N`, `no later than N`, `N ... after/from` 을 모두 잡는다.
# `within` 만 보면 SBT 의 2012 기준("no later than 30 calendar days after receipt … that sets a
# hearing date 180 calendar days after the notice")이 **통째로 안 보인다** —
# 그게 이 프로젝트의 드리프트 사례 중 가장 큰 것인데.
DUR = re.compile(
    r"(?:within|no later than|no more than)\s+([\w-]+)\s+(calendar days|business days|days|months)"
    r"|([\w-]+)\s+(calendar days|business days|days|months)\s+(?:after|from|following)",
    re.I)


BLOCK = re.compile(r"</?(p|li|tr|td|th|div|h[1-6]|table|ul|ol|br)\b[^>]*>", re.I)


def plain(chunk):
    """블록 태그만 줄바꿈으로, 인라인 태그(<strong>, <abbr>…)는 **공백**으로 바꾼다.
    전부 줄바꿈으로 바꾸면 문장이 태그 자리에서 잘린다 — 실제로 LTB 기준이
    "and A4s), will have a hearing scheduled within 25 business days." 로 잘려 나왔다."""
    chunk = re.sub(r"<script.*?</script>", " ", chunk, flags=re.S | re.I)
    chunk = BLOCK.sub("\n", chunk)
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    lines = [re.sub(r"\s+", " ", l).strip() for l in html.unescape(chunk).split("\n")]

    # 문장이 블록 태그 경계에서 잘린다. 앞줄이 문장부호로 안 끝나고 뒷줄이 소문자로
    # 시작하면 같은 문장이다. 안 이으면 2013 판 SBT 기준이
    # "calendar days after receipt of the appeal that sets a hearing date 180 calendar" 로
    # 잘려 나오고, **기간 하나가 통째로 사라진다.**
    merged = []
    for l in lines:
        if not l:
            continue
        if merged and not re.search(r"[.:;!?]$", merged[-1]) and re.match(r"[a-z(]", l):
            merged[-1] = merged[-1] + " " + l
        else:
            merged.append(l)
    return merged


def days(tok, unit):
    tok = tok.lower().replace(",", "")
    n = WORDS.get(tok)
    if n is None:
        try:
            n = float(tok)
        except ValueError:
            return None
    u = unit.lower()
    return n * 7.0 / 5.0 if u == "business days" else n * 30.0 if u == "months" else float(n)


def parse(name):
    s = text(name)
    # <h3> 로 자른다. 마지막 조각은 다음 <h3> 가 없으므로 문서 끝까지.
    parts = re.split(r"<h3[^>]*>(.*?)</h3>", s, flags=re.S | re.I)
    out = []
    for i in range(1, len(parts), 2):
        head = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", parts[i]))).strip()
        trib = NAMES.get(head)
        if not trib:
            continue
        for line in plain(parts[i + 1]):
            if len(line) < 25:
                continue
            ms = list(DUR.finditer(line))
            if not ms:
                continue
            # 한 문장에 기간이 둘이면 **더하지 않는다** — "30일 안에 통지, 그 통지로부터
            # 180일 뒤 기일" 은 210일이지만, 그 해석은 사람이 한다. 둘 다 싣는다.
            out.append({
                "source": name, "tribunal": trib, "sentence": line,
                "durations": [
                    {"as_written": f"{(m.group(1) or m.group(3))} {(m.group(2) or m.group(4))}",
                     "days": days(m.group(1) or m.group(3), m.group(2) or m.group(4))}
                    for m in ms],
            })
    return out


def main():
    rows = []
    for n in ("std_2012", "std_2013"):
        r = parse(n)
        print(f"  {n}: tribunal {len({x['tribunal'] for x in r})}곳 · 기간 문장 {len(r)}개")
        rows += r
    json.dump({"rows": rows, "provenance": provenance()},
              open(os.path.join(ROOT, "data", "standards.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"  전체 {len(rows)}문장 → data/standards.json")


if __name__ == "__main__":
    main()
