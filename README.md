# nonclinical-safety-nam-dossier

A Claude skill that writes a **NAM-first nonclinical safety assessment memo** for a
small-molecule compound, or for a target plus indication. NAM means new approach
methods: in vitro, in silico and in chemico methods, proposed before any animal study.
Each claim in the memo is traced to a logged connector query.

> **Decision support only.** The output is a starting point for a qualified
> toxicologist. It is not a regulatory document, and it does not replace expert
> review, GLP studies or agency consultation.

## Repository layout

```
.
├── README.md
├── skills/
│   └── nonclinical-safety-nam-dossier/
│       ├── SKILL.md                     # frontmatter + workflow + hard rules
│       ├── references/
│       │   ├── liability_taxonomy.yaml  # controlled liability codes — single source of truth
│       │   ├── liability_taxonomy.md    # how to classify; human notes
│       │   ├── connectors.md            # what each source can and cannot show (TODO)
│       │   ├── nam_catalog.md           # risk → NAM options → animal triggers (TODO)
│       │   └── guidelines.md            # ICH / FDA / OECD notes, ALL unverified (TODO)
│       ├── schemas/
│       │   └── dossier.schema.json      # JSON sidecar contract (read by evals)
│       └── templates/
│           └── memo_template.md         # human-readable memo layout
└── evals/
    ├── cases.yaml                       # suggested cases (TODO: confirm)
    ├── ground_truth/                    # _TEMPLATE.yaml + one per case, unfilled
    ├── runs/                            # <case_id>/run_{1,2,3}.json  (skill outputs)
    ├── fixtures/                        # synthetic data for the smoke test
    ├── reports/                         # generated eval reports (git-ignored)
    ├── report_template.md               # report shape + metric definitions
    ├── run_eval.py
    └── requirements.txt
```

## What still needs filling in

The scaffolding is complete and the harness runs. These are expert-judgement files,
left as structured TODOs:

| File | What's needed |
|---|---|
| `references/nam_catalog.md` | The actual NAM entries per liability. Structure and required fields are specified; the methods are yours to write. |
| `references/guidelines.md` | Guideline entries, looked up rather than recalled. Everything stays `needs_human_verification` permanently. |
| `references/connectors.md` | Per-source "cannot support" and gotcha notes, from your own use of each connector. |
| `references/liability_taxonomy.yaml` | Codes beyond the five mandatory ICH S7A / genotoxicity domains. |
| `evals/cases.yaml` | Confirm or replace the suggested compounds. |
| `evals/ground_truth/*.yaml` | Liability lists verified against current labels. |

## Using the skill

Import this repo (or just the `skills/nonclinical-safety-nam-dossier/` folder) as a
skill. The skill expects these connectors to be available:

| Step | Connectors |
|---|---|
| Identity | PubChem, ChEMBL, UniProt |
| Target-level risk | GTEx, Human Protein Atlas, Open Targets, STRING, PubMed |
| Off-target signals | ChEMBL, BindingDB |
| Class signals | openFDA (drug labels, FAERS) |

If a connector is missing, the skill records it as `not_assessed` and keeps going. It
never fills the gap from memory.

Example prompts:

- "Nonclinical safety dossier for bosentan in pulmonary arterial hypertension."
- "NAM-first safety assessment for a small-molecule NLRP3 inhibitor for gout."

Each run produces two files:

1. `memo.md`, the memo for the toxicologist (layout in `templates/memo_template.md`)
2. `dossier.json`, the machine-readable version, validated against
   `schemas/dossier.schema.json`

## Running the evals

```bash
pip install -r evals/requirements.txt
```

1. Fill in and verify `evals/ground_truth/<case_id>.yaml` from the current FDA label
   (DailyMed), then set `verified: true`. Recall and false-alarm scores are skipped
   for any case that is still unverified.
2. Run the skill 3 times per case and save each `dossier.json` to
   `evals/runs/<case_id>/run_1.json` … `run_3.json`.
3. Score:

```bash
python evals/run_eval.py --runner offline
```

The harness writes `evals/reports/<timestamp>/report.md` and `results.json`.
Add `--strict-schema` to exit non-zero when a run violates `dossier.schema.json`.

To check the harness itself without any real data:

```bash
python evals/run_eval.py --cases evals/fixtures/cases.yaml --ground-truth evals/fixtures/ground_truth --runs-dir evals/fixtures/runs --strict-schema
```

The fixture runs are built to trip every check, so a healthy smoke test *reports
problems*. `evals/fixtures/README.md` lists the expected numbers.

### What gets scored

| Metric | Definition |
|---|---|
| **Recall** | Share of label-documented liabilities that the skill flagged with status `signal`. Averaged over runs. |
| **False alarms** | Liabilities flagged as `signal` that the ground truth lists as `absent_liabilities` (negative controls). Flags that are neither expected nor listed as absent are reported for human review and not scored. |
| **Citation validity** | Share of claims whose citations resolve: the cited query IDs exist in the query log, the cited record IDs appear in those queries' results, and the status rules hold (see `run_eval.py`). |
| **Consistency** | Mean pairwise Jaccard similarity of the flagged-liability sets across the 3 runs, plus agreement on confidence level for liabilities flagged in every run. |

Recall and false alarms are skipped for any case whose ground truth is still
`verified: false`, since scoring against an unverified answer key produces a number
that looks like a result and isn't one. Citation validity and consistency need no
ground truth and are always scored. The harness also reports rule violations that
aren't metrics: guideline references not marked `needs_human_verification`, mandatory
liabilities missing from a dossier, unknown liability codes, and schema errors.

Full definitions, and notes on how to read a report, are in
`evals/report_template.md`.

### Adding an API runner

`run_eval.py` has a `Runner` interface. `OfflineRunner` reads saved outputs.
`ClaudeApiRunner` is a stub showing where to call the Claude API with the skill and
connectors attached and save each output to `runs/`.
