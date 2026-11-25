# Connector notes

One section per data source the workflow uses. Each says what the source can support,
what it cannot, and which stable IDs belong in a query log entry's
`returned_record_ids`.

Tool names differ between deployments, so the skill logs the exact tool name it
called rather than a name from this file.

**TODO (owner): fill in each section below.** The headings and the questions under
them are the structure; the answers should come from your own use of each connector,
since the fields a deployment exposes vary. Until a section is filled in, the skill
still logs queries against that source, but it has no guidance on how to read them.

For each connector, write:

1. **Use for** — the questions in the workflow this source can answer.
2. **Record IDs** — the stable identifier to log per returned record.
3. **Cannot support** — the inferences this source does *not* license. This is the
   most valuable part of each section. A measurement is not the thing a reader will
   assume it is: transcript abundance is not protein abundance, a curated interaction
   is not a toxicological finding, a spontaneous report is not an incidence rate, and
   an approved drug's label is not evidence about a different molecule.
4. **Gotchas** — organism and assay-type fields to check, units, thresholds to state
   explicitly, data-quality or reliability flags the source itself publishes.

---

## PubChem

*Step 1, identity.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO
- Gotchas: TODO

## ChEMBL

*Step 1, identity and mechanism. Step 3, off-target activities. Step 4, class members.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO
- Gotchas: TODO — note at minimum which fields record organism and assay type, and
  which activity types are comparable to each other.

## UniProt

*Step 1, target identity.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO
- Gotchas: TODO

## GTEx

*Step 2, normal-tissue expression.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO
- Gotchas: TODO

## Human Protein Atlas

*Step 2, protein-level and cell-type-level expression.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO
- Gotchas: TODO — note the reliability or validation flags HPA publishes alongside a
  result, and how the skill should report a low-reliability one.

## Open Targets

*Step 2, known target safety information and genetic associations.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO
- Gotchas: TODO — note that entries aggregate underlying sources, and say whether the
  skill should cite the aggregate or the underlying record.

## STRING

*Step 2, pathway and partner context.*

- Use for: TODO
- Record IDs: TODO — include the confidence cutoff used, not just the IDs.
- Cannot support: TODO
- Gotchas: TODO — note which evidence channels you consider weak, and whether the
  skill may use this source for anything beyond generating a hypothesis.

## PubMed

*Step 2 and Step 4, literature.*

- Use for: TODO
- Record IDs: PMID.
- Cannot support: TODO
- Gotchas: TODO — note whether the skill has full text or abstracts only, and how to
  bound a claim to the species, dose and model actually studied.

## BindingDB

*Step 3, measured affinities.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO
- Gotchas: TODO — note how to handle units, and whether any unit conversion is
  allowed (if it is, the dossier must show the conversion).

## openFDA — drug labels

*Step 4, class signals.*

- Use for: TODO
- Record IDs: TODO — include the label section name alongside the identifier.
- Cannot support: TODO
- Gotchas: TODO

## openFDA — adverse event reports

*Step 4, optional class signals.*

- Use for: TODO
- Record IDs: TODO
- Cannot support: TODO — be explicit here about what a spontaneous reporting system
  cannot tell you.
- Gotchas: TODO

---

## When a connector is unavailable or a query fails

This part is fixed, and is not a TODO:

- Log the attempt with `status: "error"` and the error text in `note`. A failed query
  is still a query log entry.
- Any liability that depended only on that source becomes `not_assessed`, never
  `no_evidence_found`. The difference is the whole point: one means nothing was
  found, the other means nobody looked.
- Add a line to the memo's Limitations naming the missing source and the questions it
  would have answered.
- Do not fill the gap from background knowledge. See SKILL.md hard rule 1.
