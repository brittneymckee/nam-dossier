# Nonclinical Safety Assessment — NAM-First Dossier

**{{compound_or_target}}** · {{indication}}
Generated {{generated_at}} · schema {{schema_version}}

> **Decision support only.** This memo is a starting point for a qualified
> toxicologist. It is assembled from public database queries, each logged in the
> appendix. It is not a regulatory document, it does not constitute a safety
> assessment or a go/no-go recommendation, and it does not replace expert review, GLP
> studies or consultation with a regulatory agency. Every guideline reference below is
> unverified and must be checked against the issuing body's current text before use.

---

## 1. Executive summary

<!--
Only claims that already appear in the evidence table. No number that is not in a
cited query result. No ranking against other compounds, no go/no-go.
State the shape of the evidence base, including where it is thin.
-->

{{summary_paragraph}}

**Coverage at a glance**

| Status | Count | Meaning |
|---|---:|---|
| Signal | {{n_signal}} | Evidence points toward the risk |
| No evidence found | {{n_no_evidence}} | Queries ran, nothing relevant returned — not a clean result |
| Evidence against risk | {{n_against}} | Positive data against the risk, with record IDs |
| Not assessed | {{n_not_assessed}} | Nobody looked: connector unavailable, query failed, or out of scope |

---

## 2. Identity

| Field | Value | Query |
|---|---|---|
| Compound | {{name}} | {{query_ids}} |
| PubChem CID | {{cid}} | {{query_ids}} |
| ChEMBL ID | {{chembl_id}} | {{query_ids}} |
| InChIKey | {{inchikey}} | {{query_ids}} |
| Salt / parent | {{salt_parent}} | {{query_ids}} |
| Primary target(s) | {{targets}} | {{query_ids}} |
| UniProt | {{uniprot}} | {{query_ids}} |

<!-- Omit a row rather than leaving a value unsourced. -->

**Unresolved identity questions**

{{unresolved_list}}

<!-- Ambiguous CIDs, salt/parent mismatch, a gene symbol mapping to several proteins.
     "None" only if identity resolved cleanly. -->

---

## 3. Liability summary

| Liability | Status | Confidence | Mechanism basis | Claims |
|---|---|---|---|---|
| {{liability_label}} | {{status}} | {{confidence}} | {{mechanism_basis}} | {{claim_ids}} |

Confidence describes **how strong the evidence is**, not how likely harm is.
`No evidence found` and `Not assessed` carry no confidence value.

Write each `no_evidence_found` row's note as *"not detected in {{sources_searched}}"*.
Never as "no risk", "clean" or "negative".

---

## 4. Evidence

| Claim | Statement | Liability | Status | Confidence | Queries | Records |
|---|---|---|---|---|---|---|
| {{claim_id}} | {{statement}} | {{liability_code}} | {{status}} | {{confidence}} | {{query_ids}} | {{record_ids}} |

**Quantities** — every number, as reported by the source, with no conversion unless
the conversion is shown:

| Claim | Quantity | Value as reported | Units | Record |
|---|---|---|---|---|
| {{claim_id}} | {{quantity}} | {{value_as_reported}} | {{units}} | {{record_id}} |

**Conflicts and caveats**

{{uncertainty_notes}}

<!-- Disagreement between sources, assay-type or species caveats, reliability flags
     the source itself published. Do not resolve a conflict silently. -->

---

## 5. NAM-first testing plan

Ordered cheapest and most decision-relevant first. A NAM-first plan reduces, refines
and re-sequences animal use. It does not claim to remove it, and it does not predict
what a regulator will accept.

### {{liability_label}} — {{status}}

| # | Assay | Tier | Measures | Decision it informs | What a negative result does *not* establish |
|---:|---|---|---|---|---|
| 1 | {{assay}} | {{tier}} | {{measures}} | {{decision_informed}} | {{limits}} |

**Would still call for in vivo work:** {{animal_study_trigger}} → {{study}}
*Guideline refs: {{guideline_ref_ids}} — all unverified, see §8.*

<!-- Where references/nam_catalog.md has no entry for this liability, say so: state
     the decision that needs resolving and that the method is not yet specified.
     Do not invent an assay. -->

---

## 6. Open questions

{{open_questions_list}}

<!-- Anything that would otherwise be an uncited claim lives here, phrased as a
     question, with what was looked for and why it stayed open. -->

---

## 7. Limitations

{{limitations_list}}

<!-- Unavailable connectors and the questions they would have answered; missing
     indication; thresholds and filters applied; domains out of scope; the fact that
     all evidence here is public-database evidence and none of it is compound-specific
     experimental work commissioned for this program. -->

---

## 8. Guideline references — all pending human verification

| Ref | Body | Designation | Title | Source | In repo | Note |
|---|---|---|---|---|---|---|
| {{ref_id}} | {{issuing_body}} | {{designation}} | {{title}} | {{source_url}} | {{in_repo}} | {{uncertainty_note}} |

**Every row above is unverified.** Numbering and section structure change between
revisions, documents are withdrawn and replaced, and regional implementations
diverge. Check each against the issuing body's current text before relying on it or
citing it onward. Where the designation is blank, this repo had no entry and none was
supplied from memory.

---

## 9. Appendix — query log

Every connector call made for this memo, including failures and empty results.

| Query | Connector | Tool | Parameters | Run at | Status | n | Records used |
|---|---|---|---|---|---|---:|---|
| {{query_id}} | {{connector}} | {{tool}} | {{params}} | {{executed_at}} | {{status}} | {{n_results}} | {{returned_record_ids}} |

Queries with status `error` or `empty` are listed deliberately: they mark where the
evidence base has holes, and which liabilities are therefore `not_assessed` rather
than `no_evidence_found`.

---

> **Decision support only.** Nothing in this memo is a safety determination. A
> `no evidence found` result means the queries listed above returned nothing
> relevant, not that the risk is absent. No assay data in this memo was generated for
> this compound; all of it is drawn from the public sources logged in §9. Guideline
> references in §8 are unverified. Review by a qualified toxicologist is required
> before any of this informs a decision.
