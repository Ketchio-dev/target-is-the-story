"""어느 기준이 '첫 심리까지의 기한'인가 — **규칙 한 벌.** 여기 말고는 두지 않는다.

이 파일이 생긴 이유: 같은 규칙을 `analyze.py` 와 `export_web.py` 가 **따로** 들고 있었고,
고칠 때 한쪽만 고쳤다. 그 결과 OSETS 의 20일 기준이 **화면에서만** 사라졌다 —
터미널은 17행, 화면은 16행. 시계 시작점 가짓수도 12 대신 11 로 찍혔다.

빠진 문장은 이것이다:

    "Percentage that the OSETs **proceed** to a first held pre-hearing event within 20 days ..."

`proceeds` 가 아니라 `proceed` 다. 복수형이라 `proceeds to a first` 리터럴에 안 걸린다.
**이 프로젝트에서 OSETS 가 필터에 조용히 지워진 것은 이번이 두 번째다** — 앞번은 롤업
정규식이었고 그때는 격차가 -2.7 대신 -4.2 로 부풀었다. OSETS 는 목표가 **짧아진 유일한**
심판소, 즉 쉬운 이야기를 반증하는 행이다. 필터가 반례부터 지운다.

부수효과가 없다. `analyze.py` 를 가져다 쓰면 분석 전체가 돌아 버리므로(가드가 없다)
규칙만 여기로 뺐다.
"""
import re

# "첫 사건에 도달했다" 계열. proceeds? 로 단·복수를 모두 받는다.
FIRST_EVENT = re.compile(
    r"proceeds?\s+to\s+a\s+first\s+(held\s+hearing\s+event|held\s+pre-hearing\s+event"
    r"|telephone\s+review|pre-hearing)", re.I)

# "심리가 잡혔다" 계열.
SCHEDULED = re.compile(r"hearings? scheduled within", re.I)


# ── 사다리에 무엇이 들어가는가 ────────────────────────────────────────────────
# **열거하지 않고 배제한다.** 앞 판본은 "이런 표현이면 넣는다"는 목록이었고,
# 목록에 없는 표현이 나올 때마다 조용히 빠졌다. 세 번 빠졌다:
#   1) OSETS 롤업 — `proceeds` 를 요구해서 `proceed` 를 놓쳤다
#   2) OSETS 사다리 — export_web 의 제 사본이 같은 실수를 반복했다
#   3) **LAT 20일(n=13,766)과 ARB 90일(n=5,001)** — 목록에 없는 표현이었다.
#      LAT 문장은 글자 그대로 "the first hearing event (i.e., a case conference)
#      is scheduled within 20 calendar days" 다. 빠질 이유가 없었다.
#
# 그래서 규칙을 뒤집었다. **사건까지의 기한이면 들어가고, 아래 둘이면 빠진다:**
#   · "from/after the conclusion of ..." — 심리가 **끝난 뒤**의 기한이다(결정문 발송 등)
#   · "lifecycle" — 사건 **전체** 기간이지 첫 사건까지가 아니다
# 넣을 이유를 대는 대신 **뺄 이유를 대게** 했다. 새 표현은 기본값이 '포함'이다.
EVENT = re.compile(r"(hearing|review|mediation|pre-hearing|case conference)", re.I)
POST = re.compile(r"(from|after)\s+the\s+conclusion\s+of", re.I)
LIFECYCLE = re.compile(r"lifecycle", re.I)


def is_first_hearing(standard):
    """그 기준이 **첫 사건까지의 기한**을 재는가. 뺄 이유가 있어야 뺀다."""
    if not EVENT.search(standard):
        return False
    if POST.search(standard) or LIFECYCLE.search(standard):
        return False
    return True


# 경계에 있는 둘은 숨기지 않고 여기 적는다. 둘 다 사다리에 **들어간다**:
#   · ARB "the hearing event month is assigned within 90 days" — 심리가 잡힌 것이 아니라
#     **달이 배정된** 것이다. 다른 행보다 약한 약속인데, 그게 바로 이 사다리가 보이려는 것이다.
#   · HRTO "mediations scheduled within 150 calendar days from the date the parties agreed
#     to mediation" — 심리가 아니라 조정이고, 시계도 신청이 아니라 **합의**에서 시작한다.
# 둘을 빼면 "같은 퍼센트가 서로 다른 것을 센다"는 논지가 오히려 약해진다.
