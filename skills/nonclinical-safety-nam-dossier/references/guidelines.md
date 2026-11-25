# Guideline notes

**Every reference in this file is unverified, and stays that way.** Hard rule 4: the
skill marks each guideline reference it emits as
`verification: needs_human_verification`, and nothing in this repo — not this file,
not a filled-in entry, not a reviewed PR — marks one as verified. Verification
happens outside the repo, against the issuing body's current text, by a person who is
accountable for the citation.

That is not a formality. Guideline numbering changes between revisions, sections get
renumbered, documents are withdrawn and replaced, and regional implementations
diverge. A model's recall of a section number is not reliable, and a wrong citation
in a safety document is worse than no citation.

**TODO (owner): fill in the entries you want the skill to be able to reach for.**

## Required shape of an entry

```yaml
id: <short key the NAM catalog and dossier refer to>
issuing_body: ICH | FDA | EMA | OECD | other
designation: <document identifier as the issuing body writes it>
title: <document title>
revision: <revision or version, if the body uses one>
scope: <what the document covers, in one or two lines>
relevance: <which liability codes or workflow steps it bears on>
source_url: <link to the issuing body's own page, not a secondary summary>
retrieved: <date you last checked the source>
verification: needs_human_verification
```

`source_url` points at the issuing body. A secondary summary is not a citation, and
the skill must never present one as the primary reference.

## Entries to write

Grouped by what the workflow needs them for. Designations are deliberately left
blank: look each one up rather than filling in a remembered number.

- [ ] General nonclinical package and its timing relative to clinical trials
- [ ] Safety pharmacology core battery — cardiovascular, CNS, respiratory
- [ ] Cardiac electrophysiology and proarrhythmia assessment, including any
      questions-and-answers or addendum documents that modify the parent guideline
- [ ] Genotoxicity testing battery
- [ ] Carcinogenicity assessment
- [ ] Reproductive and developmental toxicity
- [ ] Oncology-specific nonclinical expectations, where risk tolerance differs
- [ ] Test-method guidelines for the specific NAMs in `nam_catalog.md`
- [ ] Any regional guidance that diverges from the above for your target markets

## How the skill cites these

- A dossier reference carries the `id` from this file, plus the
  `needs_human_verification` marker. It does not restate the designation from
  memory.
- If the skill needs a guideline that has no entry here, it says the reference is not
  available in the repo and flags it as an open question. It does not supply a
  designation from background knowledge.
- Uncertainty is stated, not smoothed. "A section covering X exists but I could not
  confirm its number" is an acceptable thing for a dossier to say, and is better than
  a confident wrong number.
