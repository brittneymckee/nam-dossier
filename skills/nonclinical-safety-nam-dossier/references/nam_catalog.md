# NAM catalog

A menu of new approach methods per liability code, used by Step 6 of the workflow to
turn each identified risk into a proposed experiment.

**TODO (owner): this catalog is unfilled, and filling it is expert work.** Assay
selection, concentration ranges, acceptance criteria and the question of what a given
result licenses are judgement calls that belong to a toxicologist and to the testing
lab that will run the work. Write it from your own domain knowledge and current
method guidance, not from a model's recall.

Until it is filled in, Step 6 can still state the *decision* each liability needs
resolved, and should say plainly that the specific method is not yet specified rather
than invent one.

## Required shape of an entry

One block per liability code, with methods ordered cheapest and most
decision-relevant first — in silico, then biochemical, then cell-based, then complex
in vitro such as microphysiological systems and organoids.

```yaml
liability_code: <code from liability_taxonomy.yaml>
methods:
  - method: <assay name>
    tier: in_silico | biochemical | cell_based | complex_in_vitro
    measures: <the physical quantity or endpoint it reports>
    informs: <the decision this result would move, and in which direction>
    limits: <what a negative result does NOT establish>
    guideline_refs:
      - ref: <ICH / FDA / EMA / OECD identifier>
        verification: needs_human_verification
animal_study_triggers:
  - trigger: <result or regulatory need that would still call for in vivo work>
    study: <which study>
    guideline_refs:
      - ref: <identifier>
        verification: needs_human_verification
```

Two fields matter more than the rest and are easy to leave thin:

- **`limits`** keeps hard rule 2 intact at the planning stage. A NAM that comes back
  negative yields `no_evidence_found` for the thing it measured, which is narrower
  than the liability. Write down that gap when you specify the assay.
- **`animal_study_triggers`** keeps the skill honest about scope. A NAM-first plan
  reduces and refines animal use and sequences it later. It does not claim to remove
  it, and it does not decide what a regulator will accept. Where in vivo data is
  still generally expected, the entry should say so rather than imply a non-animal
  package is sufficient.

## Entries to write

One per mandatory code in `liability_taxonomy.yaml`, at minimum:

- [ ] `cv_qt_proarrhythmia`
- [ ] `cv_hemodynamic`
- [ ] `cns_neurotoxicity`
- [ ] `respiratory`
- [ ] `genotoxicity`
- [ ] one per additional code you add to the vocabulary

## Notes for whoever fills this in

- Keep guideline references separate from method descriptions, so the verification
  state travels with the reference rather than with the assay.
- If a method's standing is contested or still evolving, record that in `limits`. A
  dossier that cites a method as settled when it isn't is worse than one that says
  the question is open.
- Prefer naming the endpoint over naming a vendor platform, so an entry stays usable
  when a lab switches suppliers.
