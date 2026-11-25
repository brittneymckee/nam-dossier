# Eval report template and metric definitions

`run_eval.py` generates `reports/<timestamp>/report.md` in this shape, plus a
`results.json` with the full detail. This file documents what each number means, so
a reader doesn't have to infer it from the code.

## Shape of a report

```
# Eval report — nonclinical-safety-nam-dossier
Run <timestamp> · runner <name> · <n> cases

## Headline
| Metric | Value | Basis |
Recall (unweighted) / False alarms / Citation validity / Consistency /
Flags needing human review

> warning if any case has unverified ground truth

## Per case
### <case_id> (<case_kind>)
- Runs loaded
- Scope guard verdict, for out_of_scope cases
- Recall, unweighted and weighted, per run
- Expected liabilities answered `no_evidence_found`
- False alarms
- Citation validity
- Consistency, confidence agreement
- Citation problems, grouped by kind
- Rule and schema problems
- Flags needing human review
- Ground-truth notes, not scored
```

## Metric definitions

### Recall

Share of a case's `expected_liabilities` that a run flagged with status `signal`,
averaged over runs. Reported unweighted and weighted, where weights come from the
ground truth (so a boxed warning can count for more than a passing mention).

**Only `signal` counts.** An expected liability answered `no_evidence_found` is a
miss, and it is reported on its own line because it is a different failure from
silence: the skill looked and came up empty, which may mean the public sources really
don't carry it. That distinction is worth seeing rather than averaging away.

Skipped when ground truth has `verified: false`.

### False alarms

Count of `signal` flags on liability codes the ground truth lists in
`absent_liabilities`, per run and summed.

This metric is only as good as `absent_liabilities`. The template tells you to be
conservative there, because a code listed absent on thin grounds turns a correct find
into a scored failure. An absence you're unsure of belongs in `unscored_notes`.

`no_evidence_found` on an absent liability is **not** a false alarm. It is the correct
outcome, and it is not counted anywhere.

Skipped when ground truth has `verified: false`.

### Flags needing human review

`signal` flags on codes that are in neither `expected_liabilities` nor
`absent_liabilities` nor `acceptable_extra_flags`.

**Not scored, by design.** The harness cannot tell a hallucinated liability from a
real one the answer key doesn't cover, and guessing either way would corrupt both
recall and false alarms. These are listed for a person to adjudicate: each one either
belongs in `expected_liabilities` / `acceptable_extra_flags`, or in
`absent_liabilities`. The pile should shrink as the ground truth matures.

### Citation validity

Share of a run's claims whose citations all resolve. A claim is valid when:

1. it cites at least one `query_id` (hard rule 1)
2. every cited `query_id` exists in the run's `query_log`
3. every cited `record_id` appears in some cited query's `returned_record_ids`
4. every `quantities[].record_id` is itself among those records (hard rule 3: a
   number must come from a record the claim actually cites)
5. the claim does not rest *only* on queries whose status is `error` or `empty`

Rule 5 catches the citation-shaped version of the `no_evidence_found` confusion: IDs
that resolve, pointing at queries that found nothing.

Needs no ground truth, so it is always scored.

### Consistency

Mean pairwise Jaccard similarity of the `signal` sets across runs. 1.0 means every
run flagged exactly the same liabilities.

Also reported: **confidence agreement**, the share of liabilities flagged in *every*
run where all runs assigned the same confidence level. A high Jaccard with low
confidence agreement means the skill finds the same risks but can't grade the
evidence stably, which is a different problem from finding different risks.

Needs no ground truth, so it is always scored.

### Rule and schema problems

Not a score, a checklist. Flags per run:

- guideline references whose `verification` is anything other than
  `needs_human_verification` (hard rule 4 has no other permitted value)
- mandatory liability codes missing from `liabilities` entirely, which hides a gap
  instead of showing it as `no_evidence_found` or `not_assessed`
- liability codes absent from `liability_taxonomy.yaml`
- schema violations against `dossier.schema.json`

Any of these should be fixed before the headline numbers mean much.

## Reading a report

A few combinations worth recognising:

| Pattern | Likely reading |
|---|---|
| High recall, many false alarms | The skill flags broadly. Check whether `signal` is being used where `no_evidence_found` belongs. |
| High recall, low citation validity | It reaches the right conclusions by the wrong route. Hard rule 1 is not holding, and the output isn't traceable even when it's right. |
| Low recall, high citation validity | Disciplined but under-searching. Look at whether Step 2 and Step 3 queries are too narrow, and at how many liabilities come back `not_assessed`. |
| High Jaccard, low confidence agreement | Stable findings, unstable grading. Look at the confidence rubric in SKILL.md Step 5. |
| Large review pile | The ground truth is immature, not necessarily the skill. Adjudicate the pile first. |
| Many `not_assessed` | Connectors were missing. Valid behaviour, but the run says little about skill quality. Check connector availability before reading anything else. |

## TODO (owner)

- [ ] Decide a target for each metric before reading the first real report, so the
      numbers are judged against a prior rather than rationalised after the fact.
- [ ] Decide what counts as a regression worth blocking on.
- [ ] Record the model ID and date alongside each report. Results are not comparable
      across model versions.
