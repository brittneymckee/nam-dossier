# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this repo is

A Claude skill, plus an eval harness for it. The skill writes a **NAM-first
nonclinical safety assessment memo** for a small-molecule compound, or for a drug
target plus indication. NAM means new approach methods: in vitro, in silico and in
chemico methods, proposed before any animal study. Every claim in the memo is traced
to a logged connector query.

This project is built by a customer engineer to demonstrate skill design to Life
Sciences customers. None of its outputs are for commercial, clinical or research use.

**Nothing here is a regulatory document, and nothing here produces one.** The skill's
output is decision support for a qualified toxicologist. It does not replace expert
review, GLP studies or agency consultation. Keep that framing in every file you write.

## Layout

```
skills/nonclinical-safety-nam-dossier/
  SKILL.md          # frontmatter, hard rules, 7-step workflow, self-check
  references/       # connector notes, liability taxonomy, NAM catalog, guideline notes
  schemas/          # dossier.schema.json, the JSON sidecar contract
  templates/        # memo_template.md
evals/
  cases.yaml        # eval cases
  ground_truth/     # one YAML per case, verified by the repo owner
  runs/             # <case_id>/run_{1,2,3}.json, saved skill outputs
  reports/          # generated, git-ignored
  run_eval.py
```

`README.md` is the user-facing doc. Keep it in step with SKILL.md.

## Hard rules of the skill

`SKILL.md` carries five hard rules. They are the point of the skill, not boilerplate.
Do not relax, condense or make them optional, and do not add a workflow step that
would need one of them broken:

1. No claim without a traceable query. Each claim cites at least one `query_id` from
   the query log. Background knowledge decides what to query; it is never evidence.
2. "No evidence found" is not "evidence of no risk". The four statuses
   (`signal`, `no_evidence_found`, `evidence_against_risk`, `not_assessed`) stay
   distinct everywhere: SKILL.md, the schema, the memo template and the scoring.
3. Never invent assay data. No IC50s, Ki values, exposure margins, expression values,
   FAERS counts or label text that a query did not return. No estimates, no
   interpolation.
4. Every guideline reference (ICH, FDA, EMA, OECD) is marked
   `verification: needs_human_verification`. Nothing in this repo marks a guideline
   reference as verified.
5. The decision-support disclaimer appears at the top and bottom of the memo and in
   `dossier.json`.

If you write an example, a fixture or a test, it must obey these rules too. An example
memo with an uncited number teaches the wrong thing.

## Conventions

- **Liability codes** live in `references/liability_taxonomy.md`. The enum in
  `schemas/dossier.schema.json`, the ground-truth files and `run_eval.py` all use the
  same codes. Changing a code means changing all four places.
- **Two outputs per run**: `memo.md` for the human, `dossier.json` for the harness.
  They must agree: same claims, same IDs, same statuses.
- **Fake data is labelled.** Any sample `dossier.json` used to exercise the harness
  goes in a path or filename that says it is a fixture, and its `query_log` entries
  are obviously synthetic. Never place a fixture under `evals/runs/`, which is for
  real recorded outputs.
- **Reference notes stay cautious.** `references/` tells the model what each source
  cannot support (GTEx RNA is not protein, STRING edges are not toxicity evidence,
  FAERS is not incidence). Preserve those caveats when editing.

## Ground truth

`evals/ground_truth/` is **verified by the repo owner against current drug labels**
(DailyMed and the FDA label), not by Claude. Do not fill in, guess at or "improve" a
liability list. Leave `verified: false` and the TODO markers alone unless the owner
says a case is verified. The harness skips recall and false-alarm scoring for
unverified cases, which is intended.

## Eval harness

`run_eval.py` scores four things. Keep the definitions in `README.md` and in the code
in step with each other:

- **recall** of label-documented liabilities flagged as `signal`; refused outright for
  a verified case whose codes aren't in the taxonomy, rather than scored wrongly
- **false alarms** against each case's `absent_liabilities` (negative controls); a flag
  that is neither expected nor listed as absent is reported for human review, not
  scored
- **citation validity**: cited query IDs exist, cited record IDs appear in those
  queries' results, and the per-status rules hold
- **consistency** across 3 runs

The default runner is offline: it scores saved outputs and needs no network and no API
key. `ClaudeApiRunner` is a stub. Keep the offline path working on its own.

## Working style here

- Python for the harness. Standard library plus `pyyaml` and `jsonschema`; ask before
  adding a dependency.
- Prefer small, readable functions over clever ones. This repo gets read by customers.
- Don't add CI, packaging or a license without being asked.
