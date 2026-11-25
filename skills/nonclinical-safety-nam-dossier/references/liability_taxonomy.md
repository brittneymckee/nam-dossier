# Liability taxonomy

The machine-readable vocabulary is [`liability_taxonomy.yaml`](liability_taxonomy.yaml),
and it is the single source of truth. `dossier.json`, the eval ground truth and
`run_eval.py` all draw codes from that file. Add a code there, once.

This file holds the human notes that don't belong in the YAML.

## How to classify

- One finding, one code. If a finding genuinely spans two liabilities, list both and
  say why in `mechanism_hypothesis`.
- `other` is a fallback, not a convenience. A dossier that uses it must describe the
  liability in prose.
- The code records **what kind of risk is in question**. The `status` and `confidence`
  fields record how good the evidence is. Don't fold those into the code.

## Mandatory domains

Entries with `mandatory: true` appear in every dossier's `liabilities` list even when
nothing was found, so that a silent gap is visible as `no_evidence_found` or
`not_assessed` rather than simply absent. See SKILL.md Step 5.

## TODO (owner)

- [ ] Extend `liability_taxonomy.yaml` to the organ systems and mechanisms you want
      scored. The YAML lists candidate domains as comments.
- [ ] Decide whether carcinogenicity is its own code or part of `genotoxicity`.
- [ ] Decide whether peripheral neuropathy is its own code or part of
      `cns_neurotoxicity`.
- [ ] Optionally fill in `panel_targets`, mapping secondary-pharmacology screening
      targets to liability codes, based on the panel your testing lab runs.
- [ ] Write the classification examples you'd want a new reviewer to read: a handful
      of real findings and the code each should get.
