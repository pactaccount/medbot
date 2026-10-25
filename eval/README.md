# MedBot agent evaluation

This evaluates a fictional clinic receptionist, not a medical diagnosis system.
It runs the same LangGraph workflow used by `/chat`. Policy answers use the explicit
`backend/data/clinic_policies.md` reference. Example PDFs are not silently treated
as additional clinic rules.

Policy answers now use an extractive source check: the model selects policy quotes,
and the application verifies each quote occurs in the policy before displaying it.
Missing, invented or malformed quotes produce an explicit abstention. General
capability replies are fixed text. This prevents displaying invented quote text;
it does not establish that a selected passage answers the question completely or
correctly. Human relevance and completeness scoring remains necessary.

Scheduling writes also require the proposed patient ID, explicit ISO date and
matching time to be present in user messages, excluding assistant guesses. A missing
or relative date requires concrete confirmation; time is normalized between AM/PM
and 24-hour notation. This conservative check can ask for clarification even when
a human might infer a date from natural language. It does not verify ownership of
a patient ID or detect every contradictory detail in a conversation.

## Execution and isolation

The 40 development scenarios in `development.json` cover policy facts, unsupported
questions, missing information, appointment operations, multi-turn context, emergency
routing and general conversation. `build_development.py` reproduces this development
file without reading the reserved `medibot_holdout.md`.

The evaluator calls the configured real model. It executes the application's actual
FastMCP tools through an in-process MCP client, substituting a fresh mongomock
collection for each scenario. A sentinel patient detects changes to unrelated records.
No hosted clinic records are read or written. This verifies agent/tool behavior with
an in-memory MongoDB substitute; it does not establish MongoDB Atlas connectivity,
stdio transport reliability, authentication, or deployed end-to-end correctness.

Install `backend/requirements.txt` and `eval/requirements.txt` in a Python environment.
The existing local environment supports these commands from the repository root:

```bash
backend/venv/bin/python eval/run.py run
backend/venv/bin/python -m pytest eval/test_evaluator.py backend/tests/unit backend/tests/integration -q
backend/venv/bin/python eval/run.py run --live --version baseline
```

The first command only validates the dataset. `--live` intentionally consumes model
provider quota. Requests are paced at three seconds minimum, automatic retries are
disabled for evaluation, and the run stops on an operational failure. Use
`--resume PATH_TO_ORIGINAL_REPORT` to carry completed cases into a new report without
repeating them. Dataset, reference policy, configured model and application hashes
must match. The original report is retained, including the failed attempt.

## What the scores mean

- **Intent accuracy:** Correct expected labels divided by completed conversation
  turns. Completion coverage and operational failures are reported alongside it.
- **Deterministic checks:** Required tool calls, exact appointment fields (including
  time and status), untouched unrelated records, absence of premature tools and
  emergency escalation wording. A passing check is not proof of a correct answer.
- **Human answer accuracy:** Pass/partial/fail against the supplied policy, expected
  behavior, and recorded tool/database facts. Reported as a pass fraction only for
  reviewed answers, with the review count shown.
- **Unsupported-claim response rate:** Fraction of reviewed conversations containing
  an invented/contradictory factual claim or unsupported action confirmation. This
  is a defined response-level hallucination measure on this sample, not a universal
  hallucination rate or a medical correctness metric.
- **Human quality:** 1–5 for relevance, completeness and clarity. A 1 is unusable,
  3 is usable with omissions, and 5 is clear and complete. Tone alone cannot override
  factual errors.
- **Reliability:** Planned, attempted, completed and failed cases; median elapsed
  case time includes workflow/model overhead and intentional request pacing.
  Model-call timing and returned token usage are recorded separately. No price or
  cost estimate is invented when provider billing is unavailable.

Unreviewed semantic scores remain null. Provider failures are not hallucinations or
zero-quality answers. The report is marked incomplete if any planned scenario is
missing or has an operational failure. Optional `--judge` adds a source-grounded
model estimate for each answer; it uses the same configured model and is not an
independent judge. Schema failures remain errors, never zero scores. It is disabled
by default to avoid extra calls and unsupported confidence.

## Review and continuous improvement

Each run writes an immutable raw report plus editable `.review.json` and readable
`.review.md` files under ignored `eval/runs/`. Review answers against their supplied
reference and recorded database facts. Record accuracy, unsupported claims, quality,
notes and a proposed correction. Only set `approved_for_regression` to true when a
human has approved a correction for reuse.

```bash
backend/venv/bin/python eval/run.py review RAW_REPORT REVIEW_JSON
backend/venv/bin/python eval/improve.py promote REVIEWED_REPORT --output eval/runs/regressions-v1.json
backend/venv/bin/python eval/run.py run --dataset eval/runs/regressions-v1.json --live --version revised
backend/venv/bin/python eval/run.py run --live --version revised
backend/venv/bin/python eval/improve.py compare BASELINE_REPORT REVISED_REPORT
```

Review merging creates a new artifact. Promotion preserves correction provenance and
refuses to overwrite previous regression datasets. The engineer then makes a targeted
prompt, tool or workflow change and checks it against both regressions and the same
development suite. Compare reports only on matching datasets and reference policies;
show regressions as well as improvements. No tool changes prompts or model weights
automatically. This is a **human-reviewed continuous improvement loop**, not automatic
model training. An implemented loop is not evidence of measured improvement until a
review/change/re-evaluation cycle has actually completed.

The user-authored 12-case holdout has now been executed once on the frozen version.
See `holdout_summary.json` and `RESULTS.md`; final human ratings are recorded.
It is no longer an unused test set. Do not promote its answers into
training/regression cases or tune prompts against it. The recorded run used the frozen development version; do not rerun it to improve the headline score. A holdout inspected during test preparation is reserved from tuning,
not a statistically blind external benchmark.

Historical `backend/tests/eval/` scripts and reports remain for context. Their results
must not be combined with this protocol: the legacy report includes provider failures,
its quality rubric lacks clinic-reference grounding, and its booking checks are partial.
The unified runner above is the current evaluation entry point.
