# Development baseline

The unified evaluator completed 40 development conversations containing 41 user turns
with `nvidia/nemotron-3.5-lightning-30b-a3b` through the configured NVIDIA API.
This is a development measurement, not a reserved-holdout result.

- Expected intent labels: **38/41 turns, 92.7%**.
- Conversations passing all applicable deterministic checks: **34/40, 85.0%**.
- Emergency examples: **4/4 routed and included the expected escalation wording**.
  Four examples cannot establish real-world emergency safety.
- Baseline human review: **6/12 pass, 4/12 partial, 2/12 fail; 4/12 contain unsupported claims; quality 3.58/5**. This is a selected review sample.
- Reserved user-authored holdout: executed once; see final results below.

Intent labels failed on D02, D07 and D14. Action checks failed on D28 (cancellation),
D29 (rescheduling) and D31 (attempted cancellation for an unknown patient). The latter
cases did not call the expected action tool; completed conversation text alone is not
proof that an operation happened. Human review will determine whether the replies
are misleading, appropriately cautious, incomplete or otherwise incorrect.

The run completed across continuations. The initial attempt stopped at a provider
rate limit after 16 completed cases. Another attempt stopped when the evaluator
rejected an empty model answer. That evaluator behavior was corrected: an empty
answer now fails a response-presence check rather than being treated as a provider
outage. Failed attempts are preserved in the earlier reports; completed cases were
not repeated. The completed artifact retains provenance and model calls from those
attempts. It is not a claim that all cases ran without interruption on the first try.

The benchmark used the real agent graph and real MCP tool implementation through an
in-process protocol transport with isolated mongomock collections. It did not use
or verify hosted MongoDB. The application version measured here is preserved locally
in `.local/evaluation_baseline/`. Source and dataset hashes, summary metrics and failed
case IDs are in `baseline_summary.json`; raw answers and reviews remain local under
ignored `eval/runs/`.

The engineering checks now pass **71 offline evaluator, tool, routing, API and session
tests**. This count describes software checks, not model accuracy. The evaluation and feedback tooling has now been used for a human-reviewed correction
and development re-evaluation cycle. Updated semantic scores have now been supplied for the same 12 selected cases.

## Revised development run

The frozen `reviewed-v3-confirmed` version completed 40/40 cases. Expected intents matched on 41/41 turns; 39/40 conversations passed all applicable automated checks.

The same dataset and policy were used. Improvements in automated checks occurred on D02, D07, D14, D28, D31. Regressions: none in the completed deterministic checks.

Six user-written corrections were promoted with review provenance. Changes cover policy grounding,
intent distinctions, required action parameters and repeated tool calls. An intermediate run
revealed that prompt instructions alone still permitted unsupported clinic facts. Policy answers
therefore now display only quotations verified against the source, or abstain. This can still
select an irrelevant or incomplete passage. Another intermediate run found an invented booking
date/time; scheduling now requires those values to be confirmed in user messages.

This demonstrates the implemented feedback-to-regression-to-change-to-evaluation loop. It is
not automatic model training. The same 12 cases received **10 pass and 2 partial** human accuracy ratings,
compared with 6 pass, 4 partial and 2 fail at baseline. Mean quality improved from
**3.58 to 4.75/5**. Submitted unsupported-claim labels fell from **4/12 to 0/12**.
These are reviewer labels on a selected sample, not proof of no hallucinations: D21
still promises an availability check although no availability tool exists. This
engineer/reviewer disagreement is retained in `human_review_comparison.json`.
D03 omits the walk-in triage detail and D29 leaves the rescheduling incomplete.
The application is frozen before the final reserved evaluation. A passing development check does not establish production reliability or generalization.

## Reserved final evaluation

The frozen application completed **12/12 holdout conversations (14 user turns)**
without operational errors. All 14 intents matched the accepted labels; all 12
conversations passed the applicable deterministic checks. All three appointment
operations matched the expected database state, including the rescheduling example.
The development rescheduling failure is still retained; a successful different
holdout example does not erase it.

These are execution, routing and database-state results, **not 100% answer accuracy**.
The policy checks do not establish semantic correctness or complete coverage of the
question. Final human ratings are recorded: **12/12 marked pass, 0/12 marked as containing
unsupported claims, mean quality 4.75/5**. Reviewer notes identify omitted details
in three answers: uninsured starting price, general refill processing time and
cancellation notice. Preserve these omissions alongside the pass labels. These
sample ratings do not establish universal accuracy or zero hallucinations.
`holdout_manifest.json` records the original document and dataset hashes and fixture
choices; `holdout_summary.json` records the sanitized results. The application
source hashes match the final development version. No model/prompt changes were
made from holdout results. No repeated completed holdout questions were used.

## Completion status

The agreed local agent-evaluation work is complete: a fixed development suite,
reserved final suite, execution/database checks, source-grounding controls, human
accuracy/unsupported-claim/quality ratings, and a demonstrated reviewed-feedback
regression/improvement cycle. The application was not tuned after the holdout.
Known development partial answers and the D21 reviewer/engineer disagreement remain
documented. This is human-reviewed improvement, not automatic model training.

71 offline checks passed during implementation. No additional model calls or tests
were run to merge the final ratings. Code and documentation changes remain local
and uncommitted; the latest hosted release and MongoDB Atlas deployment have not
been verified by these in-process evaluations. Publishing and deployment verification
are separate release work, not completed claims.
