# The Target Is The Story

**Tribunals Ontario reports that it met its scheduling standard 92 % of the time. That number
is real. It just does not mean what a reader assumes.**

Two of its tribunals both reported meeting their standard **100 % of the time** last year.
One promises a first review within **24 hours**. The other promises a first hearing within
**240 days**. That is **240×** the permitted time and a difference of zero percentage points
in compliance.

A percentage like this measures whether the target was met. It does not measure how long
anyone waited, and the targets are not comparable.

## We uncovered nothing

Every number on this page is published by Tribunals Ontario, in its own annual report. The
averaging method is their own footnote in the same table:

> evenly weighted average across all tribunals that are reporting on that

What we did is sort those standards by how long they permit, recompute the roll-up the way
that footnote describes, and put the 2012 and 2013 versions of the same standards beside
today's. **No number here is ours.** The arrangement is.

## Three things the arrangement shows

**1. The ladder.** CRB at 24 hours on 176 cases; SBT at 240 days
on 7,735 cases. Both at 100 %. Across 20 first-event standards the report uses
**15 different phrasings for when the clock starts**, so two identical percentages can be
counting from different days.

**2. The average is evenly weighted across tribunals, not across cases.** The published roll-up
is 92 % on 17,665 cases. Recomputing the same 8 component rows, evenly across the 7 tribunals
they belong to:

| | |
|---|---:|
| evenly weighted across tribunals, as the footnote describes | 91.9 % |
| the same rows, weighted by the cases each tribunal reported | 89.2 % |
| difference | **-2.7 pp** |

Our reconstruction sums to 17,707 cases against the published 17,665 — a residual of +42,
because the report does not say which rows it averages. We print the residual rather than
round it away.

Meanwhile the Landlord and Tenant Board reports **77 %** on **69,228** cases in the same
report — nearly four times the roll-up's whole denominator — and does not report the roll-up's
KPI at all.

**3. One row reports on nothing.** **1 row** reports a percentage on no cases, and **8 more carry a target with the
result printed as N/A or TBD.** Those are different things: 0 % of 0 is not a percentage, and
"N/A" is a tribunal declining to report. An earlier version of this page counted them together
as nine — which is the same mistake it was written to point out. The page now lists them
separately.

## What used to be permitted

The 2012 and 2013 service standards for the same tribunals are still online. Comparing the
longest first-hearing standard for each:

| tribunal | 2012 | 2013 | 2024-25 | change | |
|---|---:|---:|---:|---|---|
| CFSRB | 20 | 60 | 60 | **unchanged** | clock start also changed |
| HRTO | 180 | 180 | 180 | **unchanged** |  |
| LTB | 30 | 35 | 50 | **+15 days** |  |
| OSETS | 120 | 120 | 60 | **-60 days** |  |
| SBT | 210 | 210 | 240 | **+30 days** | clock start also changed |

- **moved:** LTB, OSETS, SBT
- **unchanged for thirteen years:** CFSRB, HRTO

**They did not all move the same way.** One got shorter — the Ontario Special Education
Tribunals halved theirs, from 120 days to 60. If every target had grown, it would be a policy
change; moving separately and in both directions is a set of separate decisions. Where the
clock-start wording also changed, both the page and this README say so and refuse to treat the
day counts as like-for-like.

## What this is not

- **Not a claim that any tribunal is slow or bad.** A custody review and a disability-income
  appeal are not the same case, and a longer permitted time may be entirely appropriate.
- **Not legal advice.** It tells nobody what to do in their matter. It describes how a
  published percentage is built.
- **Not complete.** The 2012/2013 standards cover the seven-tribunal SJTO cluster, not all
  thirteen. Business days and months were converted to calendar days by us; every row also
  carries the wording exactly as published.

## What a blind review changed

Before submitting, five reviewers read this project with the name stripped off. Three of their
findings were real and are fixed above:

| what was wrong | why it mattered |
|---|---|
| the drift filter required the exact phrase "hearings scheduled" | "hearings **will be** scheduled" and "scheduled for **mediation or** a hearing" never matched, so CFSRB looked like it grew by 40 days when it had not — and **OSETS, the one tribunal whose target got shorter, was dropped entirely.** A filter that silently removes the counterexample is the worst kind |
| the roll-up recompute required the verb "proceeds" | "the OSETs **proceed** to a first held **pre-hearing** event" never matched, so one component tribunal was missing and the gap read −4.2 pp instead of −2.7 |
| "N/A" was counted as zero cases | 8 of the 9 rows were tribunals declining to report, not percentages on an empty denominator |

Each is now bound by a check in `src/check.py` and a planted defect in `src/sabotage.py`.

## Run it

```bash
python3 src/parse_reports.py    # three annual reports -> data/kpi.json
python3 src/parse_standards.py  # 2012 + 2013 standards -> data/standards.json
python3 src/analyze.py          # every number quoted above
python3 src/export_web.py       # web/index.html, opens from the filesystem, no server
python3 src/check.py            # 34 checks, at a denominator that cannot shrink
python3 src/sabotage.py         # break 29 things on purpose; do the checks notice?
```

## Sources

Three Tribunals Ontario annual reports (2022-23, 2023-24, 2024-25) and two archived SJTO
service-standards pages (2012, 2013). All are static HTML on `tribunalsontario.ca`, fetched
with one `curl` each — no key, no account, no JavaScript rendering.
