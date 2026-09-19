# AI use disclosure — The Target Is the Story

LexHack requires disclosure of AI use. This is the full account.

## What AI did

**Most of the writing and most of the code.** The analysis pipeline (`src/*.py`), the page
template, the check suite, the sabotage suite, the README, and this submission's body text were
drafted by Claude (Anthropic) working in an agent loop, under direction from the author.

Specifically:

- **Parsers.** `parse_reports.py` and `parse_standards.py` were written by the model, including
  the decision to bind table cells by `<th id>` / `<td headers>` rather than column position.
- **Analysis.** `analyze.py` — the ladder ordering, the roll-up recomputation, the drift
  comparison — written by the model.
- **The check and sabotage suites.** `check.py` (34 checks) and `sabotage.py` (26 planted
  defects) were written by the model, including several rounds where the model found its own
  checks to be incapable of failing and rewrote them.
- **Prose.** README and the Devpost body, except the Inspiration section.

## What AI did not do

- **No number was produced by a model.** Every figure on the page and in the write-up comes from
  Tribunals Ontario's published documents, through the parsers. Most are re-verified against
  `analyze.py`'s output by a check, and where a check existed the drift was caught. Where one did
  not, it was not: a pre-submission review found stale counts in this file and in the Devpost body
  because the binding check read only the README. Those are corrected and the check now sweeps
  every document.
- **The decisions that are the author's** are the author's: whether to submit, what the project
  should be, and the confirmation of anything the write-up asserts about the author's own life.

## About the Inspiration section

Earlier drafts of this file said the Inspiration was written by the author. That is not accurate
and it matters here more than anywhere else, so: **the model drafted it.**

What the author supplied was the fact it rests on, which is that there is no personal story. The
author has not waited on a tribunal and has no stake in one of these cases. The model asked,
was told that, and wrote the section around it rather than inventing an experience. Everything
else in that section is a project fact that a check verifies.

We would rather print this than let a judge assume the usual arrangement.

## How the AI's work was checked

This is the part worth reading, because "an AI wrote it" is only reassuring if something
independent can catch it being wrong.

1. **A fixed-denominator check suite.** 34 checks whose count cannot shrink when one fails.
   A check that silently disappears is worse than a check that fails.
2. **Sabotage testing.** 29 deliberate defects are injected into the source one at a time, and
   the suite is re-run to confirm the check aimed at each one actually turns red. Results are
   reported in three categories — caught / missed / invalid — because "the check is dead" and
   "the mutation changed no behaviour" need different fixes. Current: 29 of 29 caught.
3. **Independent recomputation, not self-agreement.** Several early checks verified only that
   the output agreed with itself. Those were rewritten so the check recomputes one side from
   the source data.
4. **Blind review.** Separate model instances, given no context beyond the artifact, were asked
   to find what was wrong. Three of the defects they found were blockers, including one filter
   that was silently deleting the single row that contradicted the project's easy story.

The honest summary: the AI wrote nearly all of it, and the AI's first drafts contained real
errors of exactly the kind this project is about — a check that could not fail, a filter that
deleted its own counterexample, `N/A` counted as zero. They were caught by machinery built to
catch them, not by trusting the output.
