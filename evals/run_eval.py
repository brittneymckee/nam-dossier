#!/usr/bin/env python3
"""Eval harness for the nonclinical-safety-nam-dossier skill.

Scores four things per case, over 3 runs:

  recall            share of label-documented liabilities flagged as `signal`
  false alarms      `signal` flags on liabilities the ground truth lists as absent
  citation validity whether each claim's citations resolve against the query log
  consistency       agreement across runs

Design notes
------------
* The default runner is offline and scores outputs already saved under runs/. No
  network, no API key. `ClaudeApiRunner` is a stub.
* Recall and false alarms are skipped for any case whose ground truth has
  `verified: false`. Scoring against an unverified answer key produces a number that
  looks like a result and isn't one. Citation validity and consistency need no
  ground truth, so they are always scored.
* A flag that is neither expected nor listed as absent is NOT scored. The eval cannot
  distinguish a hallucination from a real finding the answer key doesn't cover, so
  those go to a human-review pile instead of into a metric.
* `no_evidence_found` is never credited as a correct answer to an expected liability,
  and never counted as a false alarm on an absent one. It is a third thing, and the
  report counts it separately.

Usage
-----
    python run_eval.py                        # offline, all cases
    python run_eval.py --case p01_x --case n01_y
    python run_eval.py --runs-dir runs --out reports
    python run_eval.py --strict-schema        # fail a run that violates the schema
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import statistics
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Protocol

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml is required: pip install -r requirements.txt")

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent / "skills" / "nonclinical-safety-nam-dossier"
TAXONOMY_PATH = SKILL_DIR / "references" / "liability_taxonomy.yaml"
SCHEMA_PATH = SKILL_DIR / "schemas" / "dossier.schema.json"

SIGNAL = "signal"
NO_EVIDENCE = "no_evidence_found"
AGAINST = "evidence_against_risk"
NOT_ASSESSED = "not_assessed"
STATUSES = {SIGNAL, NO_EVIDENCE, AGAINST, NOT_ASSESSED}


# --------------------------------------------------------------------------- utils


def load_yaml(path: Path) -> Any:
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def load_json(path: Path) -> Any:
    with path.open() as fh:
        return json.load(fh)


def is_todo(value: Any) -> bool:
    """TODO markers are unfilled, not data. Treat them as absent."""
    return isinstance(value, str) and value.strip().upper().startswith("TODO")


def pct(numerator: float, denominator: float) -> float | None:
    return None if not denominator else numerator / denominator


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


# ------------------------------------------------------------------- vocabulary


def load_taxonomy() -> tuple[set[str], set[str]]:
    """Return (all codes, mandatory codes) from the single source of truth."""
    if not TAXONOMY_PATH.exists():
        return set(), set()
    data = load_yaml(TAXONOMY_PATH)
    codes, mandatory = set(), set()
    for entry in data.get("liabilities") or []:
        code = entry.get("code")
        if not code or is_todo(code):
            continue
        codes.add(code)
        if entry.get("mandatory"):
            mandatory.add(code)
    return codes, mandatory


# ----------------------------------------------------------------------- runners


class Runner(Protocol):
    """Supplies the skill's outputs for a case. Scoring never calls the model."""

    def outputs_for(self, case_id: str, runs_per_case: int) -> list[Path]:
        ...


@dataclass
class OfflineRunner:
    """Reads dossier JSON already saved under <runs_dir>/<case_id>/run_N.json."""

    runs_dir: Path

    def outputs_for(self, case_id: str, runs_per_case: int) -> list[Path]:
        case_dir = self.runs_dir / case_id
        if not case_dir.is_dir():
            return []
        found = []
        for n in range(1, runs_per_case + 1):
            path = case_dir / f"run_{n}.json"
            if path.exists():
                found.append(path)
        # Tolerate extra runs beyond runs_per_case, so a 5-run experiment still works.
        extras = sorted(
            p for p in case_dir.glob("run_*.json") if p not in found
        )
        return found + extras


@dataclass
class ClaudeApiRunner:
    """Stub. Calls the model with the skill loaded, saves outputs, returns paths.

    Deliberately unimplemented: the offline path must keep working on its own, and
    wiring this up means deciding how connectors are provided to the model, which is
    an environment question rather than a harness question.

    To implement:
      1. Read SKILL.md and references/ from SKILL_DIR, and pass them as the system
         prompt or as a skill attachment.
      2. Attach the connectors listed in README.md. Without them the skill cannot
         log a single query, and every liability becomes `not_assessed` — which the
         harness will score as valid but empty. That is correct behaviour, and it is
         also not a useful eval, so check connector availability before running.
      3. Send the case's `prompt`, request memo.md and dossier.json.
      4. Save each run to <runs_dir>/<case_id>/run_N.json. Save the memo alongside it.
      5. Record the model ID and date in a sidecar; results are not comparable across
         model versions.
    """

    runs_dir: Path
    model: str = "TODO"

    def outputs_for(self, case_id: str, runs_per_case: int) -> list[Path]:
        raise NotImplementedError(
            "ClaudeApiRunner is a stub. Use --runner offline, or implement this "
            "following the docstring."
        )


# ------------------------------------------------------------------ check results


@dataclass
class CitationIssue:
    claim_id: str
    kind: str
    detail: str


@dataclass
class RunScore:
    path: Path
    loaded: bool = True
    load_error: str | None = None
    schema_errors: list[str] = field(default_factory=list)

    declined: bool = False
    flagged: set[str] = field(default_factory=set)       # status == signal
    no_evidence: set[str] = field(default_factory=set)
    against: set[str] = field(default_factory=set)
    not_assessed: set[str] = field(default_factory=set)
    confidence_by_code: dict[str, str | None] = field(default_factory=dict)

    n_claims: int = 0
    n_valid_claims: int = 0
    citation_issues: list[CitationIssue] = field(default_factory=list)

    unknown_codes: set[str] = field(default_factory=set)
    missing_mandatory: set[str] = field(default_factory=set)
    unverified_guideline_refs: int = 0
    guideline_ref_violations: list[str] = field(default_factory=list)

    @property
    def citation_validity(self) -> float | None:
        return pct(self.n_valid_claims, self.n_claims)


# ------------------------------------------------------------------ scoring: one run


def score_citations(dossier: dict, run: RunScore) -> None:
    """A claim is valid when every citation it makes resolves.

    Checks, per claim:
      * at least one query_id (hard rule 1)
      * every cited query_id exists in the query log
      * every cited record_id appears in some cited query's returned_record_ids
      * every quantity's record_id is itself cited by the claim
      * the claim does not rest solely on queries that errored or returned nothing
    """
    log = {
        q.get("query_id"): q
        for q in dossier.get("query_log") or []
        if q.get("query_id")
    }

    for claim in dossier.get("claims") or []:
        cid = claim.get("claim_id") or "<no id>"
        run.n_claims += 1
        issues: list[CitationIssue] = []

        cited_ids = claim.get("query_ids") or []
        if not cited_ids:
            issues.append(CitationIssue(cid, "uncited", "claim cites no query"))

        known = [q for q in cited_ids if q in log]
        for missing in (q for q in cited_ids if q not in log):
            issues.append(
                CitationIssue(cid, "dangling_query", f"{missing} not in query log")
            )

        available_records: set[str] = set()
        for qid in known:
            available_records.update(log[qid].get("returned_record_ids") or [])

        for rec in claim.get("record_ids") or []:
            if rec not in available_records:
                issues.append(
                    CitationIssue(
                        cid,
                        "unbacked_record",
                        f"record {rec} not returned by cited queries",
                    )
                )

        # Hard rule 3: a number must come from a record the claim actually cites.
        for q in claim.get("quantities") or []:
            rec = q.get("record_id")
            if rec and rec not in available_records:
                issues.append(
                    CitationIssue(
                        cid,
                        "unbacked_quantity",
                        f"quantity {q.get('quantity') or '?'}"
                        f"={q.get('value_as_reported')} cites record {rec}, "
                        "which no cited query returned",
                    )
                )

        # A claim resting only on failed or empty queries is not supported, even
        # though its IDs resolve. This is the `no_evidence_found` confusion in
        # citation form.
        if known and all(log[q].get("status") in {"error", "empty"} for q in known):
            issues.append(
                CitationIssue(
                    cid,
                    "empty_support",
                    "every cited query errored or returned nothing",
                )
            )

        if issues:
            run.citation_issues.extend(issues)
        else:
            run.n_valid_claims += 1


def score_liabilities(
    dossier: dict,
    run: RunScore,
    known_codes: set[str],
    mandatory_codes: set[str],
) -> None:
    seen: set[str] = set()
    buckets = {
        SIGNAL: run.flagged,
        NO_EVIDENCE: run.no_evidence,
        AGAINST: run.against,
        NOT_ASSESSED: run.not_assessed,
    }

    for item in dossier.get("liabilities") or []:
        code = item.get("liability_code")
        status = item.get("status")
        if not code:
            continue
        seen.add(code)
        if known_codes and code not in known_codes:
            run.unknown_codes.add(code)
        if status in buckets:
            buckets[status].add(code)
        run.confidence_by_code[code] = item.get("confidence")

    run.missing_mandatory = mandatory_codes - seen


def score_guideline_refs(dossier: dict, run: RunScore) -> None:
    """Hard rule 4: there is no permitted value other than needs_human_verification."""
    for ref in dossier.get("guideline_references") or []:
        verification = ref.get("verification")
        if verification == "needs_human_verification":
            run.unverified_guideline_refs += 1
        else:
            run.guideline_ref_violations.append(
                f"{ref.get('ref_id') or '<no id>'}: verification={verification!r}"
            )


def detect_decline(dossier: dict) -> bool:
    """A declined case produces no liabilities and says why in limitations."""
    if dossier.get("liabilities"):
        return False
    text = " ".join(
        str(lim.get("limitation", "")) for lim in dossier.get("limitations") or []
    ).lower()
    return any(
        phrase in text
        for phrase in ("out of scope", "not a small molecule", "declin")
    )


def score_run(
    path: Path,
    known_codes: set[str],
    mandatory_codes: set[str],
    validator: Any | None,
) -> RunScore:
    run = RunScore(path=path)
    try:
        dossier = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        run.loaded = False
        run.load_error = str(exc)
        return run

    if validator is not None:
        run.schema_errors = [
            f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
            for err in sorted(validator.iter_errors(dossier), key=lambda e: e.path)
        ]

    run.declined = detect_decline(dossier)
    score_liabilities(dossier, run, known_codes, mandatory_codes)
    score_citations(dossier, run)
    score_guideline_refs(dossier, run)
    return run


# --------------------------------------------------------------- scoring: one case


@dataclass
class CaseResult:
    case_id: str
    case_kind: str
    verified: bool
    runs: list[RunScore] = field(default_factory=list)
    skip_reason: str | None = None

    expected_codes: set[str] = field(default_factory=set)
    absent_codes: set[str] = field(default_factory=set)
    acceptable_extra: set[str] = field(default_factory=set)
    weights: dict[str, float] = field(default_factory=dict)
    unscored_notes: list[str] = field(default_factory=list)

    recall_per_run: list[float] = field(default_factory=list)
    weighted_recall_per_run: list[float] = field(default_factory=list)
    false_alarms_per_run: list[int] = field(default_factory=list)
    expected_but_no_evidence: list[int] = field(default_factory=list)
    review_pile: dict[str, int] = field(default_factory=dict)

    decline_correct: bool | None = None
    consistency_jaccard: float | None = None
    confidence_agreement: float | None = None

    @property
    def usable_runs(self) -> list[RunScore]:
        return [r for r in self.runs if r.loaded]

    @property
    def mean_recall(self) -> float | None:
        return statistics.fmean(self.recall_per_run) if self.recall_per_run else None

    @property
    def mean_weighted_recall(self) -> float | None:
        return (
            statistics.fmean(self.weighted_recall_per_run)
            if self.weighted_recall_per_run
            else None
        )

    @property
    def mean_citation_validity(self) -> float | None:
        values = [
            r.citation_validity
            for r in self.usable_runs
            if r.citation_validity is not None
        ]
        return statistics.fmean(values) if values else None

    @property
    def total_false_alarms(self) -> int:
        return sum(self.false_alarms_per_run)


def jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return 1.0 if not union else len(a & b) / len(union)


def score_consistency(result: CaseResult) -> None:
    runs = result.usable_runs
    if len(runs) < 2:
        return

    pairs = list(combinations(runs, 2))
    result.consistency_jaccard = statistics.fmean(
        jaccard(x.flagged, y.flagged) for x, y in pairs
    )

    # Confidence agreement, over liabilities every run flagged.
    common = set.intersection(*(r.flagged for r in runs)) if runs else set()
    if common:
        agreed = sum(
            1
            for code in common
            if len({r.confidence_by_code.get(code) for r in runs}) == 1
        )
        result.confidence_agreement = agreed / len(common)


def score_case(
    case: dict,
    truth: dict,
    runner: Runner,
    runs_per_case: int,
    known_codes: set[str],
    mandatory_codes: set[str],
    validator: Any | None,
) -> CaseResult:
    case_id = case["case_id"]
    result = CaseResult(
        case_id=case_id,
        case_kind=case.get("case_kind", "unknown"),
        verified=bool(truth.get("verified")),
        unscored_notes=[n for n in (truth.get("unscored_notes") or []) if not is_todo(n)],
    )

    paths = runner.outputs_for(case_id, runs_per_case)
    if not paths:
        result.skip_reason = f"no saved runs under runs/{case_id}/"
        return result

    result.runs = [
        score_run(p, known_codes, mandatory_codes, validator) for p in paths
    ]
    score_consistency(result)

    # Scope-guard cases are pass/fail on the decline, not recall.
    if truth.get("expect_decline"):
        usable = result.usable_runs
        result.decline_correct = bool(usable) and all(r.declined for r in usable)
        return result

    if not result.verified:
        result.skip_reason = (
            "ground truth unverified — recall and false alarms not scored"
        )
        return result

    result.expected_codes = {
        e["code"]
        for e in (truth.get("expected_liabilities") or [])
        if e.get("code") and not is_todo(e["code"])
    }
    result.absent_codes = {
        e["code"]
        for e in (truth.get("absent_liabilities") or [])
        if e.get("code") and not is_todo(e["code"])
    }
    result.acceptable_extra = {
        e["code"]
        for e in (truth.get("acceptable_extra_flags") or [])
        if e.get("code") and not is_todo(e["code"])
    }
    result.weights = {
        e["code"]: float(e.get("weight", 1.0))
        for e in (truth.get("expected_liabilities") or [])
        if e.get("code") and not is_todo(e["code"])
    }

    overlap = result.expected_codes & result.absent_codes
    if overlap:
        result.skip_reason = (
            "ground truth contradicts itself: "
            f"{sorted(overlap)} listed as both expected and absent"
        )
        return result

    for run in result.usable_runs:
        if result.expected_codes:
            hits = result.expected_codes & run.flagged
            result.recall_per_run.append(len(hits) / len(result.expected_codes))

            total_w = sum(result.weights.values()) or 1.0
            hit_w = sum(result.weights.get(c, 1.0) for c in hits)
            result.weighted_recall_per_run.append(hit_w / total_w)

            # An expected liability answered with `no_evidence_found` is a miss, but
            # a different kind of miss than silence. Count it separately.
            result.expected_but_no_evidence.append(
                len(result.expected_codes & run.no_evidence)
            )

        result.false_alarms_per_run.append(len(result.absent_codes & run.flagged))

        # Neither expected nor declared absent nor pre-accepted: human review.
        for code in (
            run.flagged
            - result.expected_codes
            - result.absent_codes
            - result.acceptable_extra
        ):
            result.review_pile[code] = result.review_pile.get(code, 0) + 1

    return result


# ------------------------------------------------------------------------ reporting


def render_report(results: list[CaseResult], meta: dict) -> str:
    template_path = HERE / "report_template.md"
    lines: list[str] = []

    scored = [r for r in results if r.recall_per_run]
    overall_recall = (
        statistics.fmean([r.mean_recall for r in scored if r.mean_recall is not None])
        if scored
        else None
    )
    cv = [
        r.mean_citation_validity
        for r in results
        if r.mean_citation_validity is not None
    ]
    overall_cv = statistics.fmean(cv) if cv else None
    cons = [
        r.consistency_jaccard for r in results if r.consistency_jaccard is not None
    ]
    overall_cons = statistics.fmean(cons) if cons else None
    total_fa = sum(r.total_false_alarms for r in results)
    total_review = sum(sum(r.review_pile.values()) for r in results)

    lines.append("# Eval report — nonclinical-safety-nam-dossier")
    lines.append("")
    lines.append(f"Run {meta['timestamp']} · runner `{meta['runner']}` · "
                 f"{len(results)} cases")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append("| Metric | Value | Basis |")
    lines.append("|---|---|---|")
    lines.append(
        f"| Recall (unweighted) | {fmt_pct(overall_recall)} | "
        f"{len(scored)} verified case(s) |"
    )
    lines.append(
        f"| False alarms | {total_fa} | flags on declared-absent liabilities |"
    )
    lines.append(f"| Citation validity | {fmt_pct(overall_cv)} | all loaded runs |")
    lines.append(
        f"| Consistency (Jaccard) | {fmt_pct(overall_cons)} | mean pairwise, "
        "flagged sets |"
    )
    lines.append(f"| Flags needing human review | {total_review} | not scored |")
    lines.append("")

    unverified = [r for r in results if not r.verified and r.case_kind != "out_of_scope"]
    if unverified:
        lines.append(
            f"> **{len(unverified)} case(s) have unverified ground truth.** Recall and "
            "false alarms are not scored for them. Verify against the current label "
            "and set `verified: true`."
        )
        lines.append("")

    lines.append("## Per case")
    lines.append("")
    for r in results:
        lines.append(f"### {r.case_id} ({r.case_kind})")
        lines.append("")
        if r.skip_reason:
            lines.append(f"- **Skipped scoring:** {r.skip_reason}")
        if not r.runs:
            lines.append("")
            continue

        lines.append(f"- Runs loaded: {len(r.usable_runs)}/{len(r.runs)}")
        for run in r.runs:
            if not run.loaded:
                lines.append(f"  - `{run.path.name}` failed to load: {run.load_error}")

        if r.decline_correct is not None:
            verdict = "pass" if r.decline_correct else "FAIL"
            lines.append(f"- Scope guard: **{verdict}** (expected a decline)")
        if r.mean_recall is not None:
            lines.append(
                f"- Recall: {fmt_pct(r.mean_recall)} unweighted, "
                f"{fmt_pct(r.mean_weighted_recall)} weighted "
                f"(per run: {[fmt_pct(x) for x in r.recall_per_run]})"
            )
            if any(r.expected_but_no_evidence):
                lines.append(
                    "- Expected liabilities answered `no_evidence_found`: "
                    f"{r.expected_but_no_evidence} — a miss, but the skill did look"
                )
        if r.absent_codes:
            lines.append(
                f"- False alarms: {r.total_false_alarms} "
                f"(per run: {r.false_alarms_per_run})"
            )
        if r.mean_citation_validity is not None:
            lines.append(f"- Citation validity: {fmt_pct(r.mean_citation_validity)}")
        if r.consistency_jaccard is not None:
            lines.append(f"- Consistency: {fmt_pct(r.consistency_jaccard)} Jaccard")
        if r.confidence_agreement is not None:
            lines.append(
                f"- Confidence agreement on always-flagged liabilities: "
                f"{fmt_pct(r.confidence_agreement)}"
            )

        issues = [i for run in r.usable_runs for i in run.citation_issues]
        if issues:
            lines.append(f"- Citation problems ({len(issues)}):")
            by_kind: dict[str, int] = {}
            for i in issues:
                by_kind[i.kind] = by_kind.get(i.kind, 0) + 1
            for kind, n in sorted(by_kind.items(), key=lambda kv: -kv[1]):
                lines.append(f"  - `{kind}` × {n}")
            for i in issues[:5]:
                lines.append(f"  - {i.claim_id}: {i.detail}")
            if len(issues) > 5:
                lines.append(f"  - … and {len(issues) - 5} more, see results.json")

        hard_rule_notes = []
        for run in r.usable_runs:
            if run.guideline_ref_violations:
                hard_rule_notes.append(
                    f"`{run.path.name}`: guideline refs not marked "
                    f"needs_human_verification — {run.guideline_ref_violations}"
                )
            if run.missing_mandatory:
                hard_rule_notes.append(
                    f"`{run.path.name}`: mandatory liabilities absent from the "
                    f"dossier — {sorted(run.missing_mandatory)}"
                )
            if run.unknown_codes:
                hard_rule_notes.append(
                    f"`{run.path.name}`: codes not in the taxonomy — "
                    f"{sorted(run.unknown_codes)}"
                )
            if run.schema_errors:
                hard_rule_notes.append(
                    f"`{run.path.name}`: {len(run.schema_errors)} schema error(s), "
                    f"first: {run.schema_errors[0]}"
                )
        if hard_rule_notes:
            lines.append("- Rule and schema problems:")
            for note in hard_rule_notes:
                lines.append(f"  - {note}")

        if r.review_pile:
            lines.append("- Flags needing human review (not scored):")
            for code, n in sorted(r.review_pile.items(), key=lambda kv: -kv[1]):
                lines.append(f"  - `{code}` in {n} run(s)")
            lines.append(
                "  - Decide for each: a real finding the ground truth lacks "
                "(add to `expected_liabilities` or `acceptable_extra_flags`), or a "
                "false positive (add to `absent_liabilities`)."
            )

        if r.unscored_notes:
            lines.append("- Ground-truth notes, not scored:")
            for note in r.unscored_notes:
                lines.append(f"  - {note}")
        lines.append("")

    if template_path.exists():
        lines.append("---")
        lines.append("")
        lines.append(
            "Metric definitions: see `report_template.md` and the README."
        )
        lines.append("")

    return "\n".join(lines)


def results_to_json(results: list[CaseResult], meta: dict) -> dict:
    return {
        "meta": meta,
        "cases": [
            {
                "case_id": r.case_id,
                "case_kind": r.case_kind,
                "ground_truth_verified": r.verified,
                "skip_reason": r.skip_reason,
                "n_runs_loaded": len(r.usable_runs),
                "n_runs_found": len(r.runs),
                "expected_codes": sorted(r.expected_codes),
                "absent_codes": sorted(r.absent_codes),
                "recall_per_run": r.recall_per_run,
                "mean_recall": r.mean_recall,
                "mean_weighted_recall": r.mean_weighted_recall,
                "expected_but_no_evidence_per_run": r.expected_but_no_evidence,
                "false_alarms_per_run": r.false_alarms_per_run,
                "mean_citation_validity": r.mean_citation_validity,
                "consistency_jaccard": r.consistency_jaccard,
                "confidence_agreement": r.confidence_agreement,
                "decline_correct": r.decline_correct,
                "review_pile": r.review_pile,
                "unscored_notes": r.unscored_notes,
                "runs": [
                    {
                        "path": str(run.path),
                        "loaded": run.loaded,
                        "load_error": run.load_error,
                        "declined": run.declined,
                        "flagged": sorted(run.flagged),
                        "no_evidence_found": sorted(run.no_evidence),
                        "evidence_against_risk": sorted(run.against),
                        "not_assessed": sorted(run.not_assessed),
                        "n_claims": run.n_claims,
                        "n_valid_claims": run.n_valid_claims,
                        "citation_validity": run.citation_validity,
                        "citation_issues": [
                            {"claim_id": i.claim_id, "kind": i.kind, "detail": i.detail}
                            for i in run.citation_issues
                        ],
                        "unknown_codes": sorted(run.unknown_codes),
                        "missing_mandatory": sorted(run.missing_mandatory),
                        "unverified_guideline_refs": run.unverified_guideline_refs,
                        "guideline_ref_violations": run.guideline_ref_violations,
                        "schema_errors": run.schema_errors,
                    }
                    for run in r.runs
                ],
            }
            for r in results
        ],
    }


# ----------------------------------------------------------------------------- main


def build_validator(strict: bool) -> Any | None:
    if not SCHEMA_PATH.exists():
        return None
    try:
        import jsonschema
    except ImportError:
        if strict:
            sys.exit("--strict-schema needs jsonschema: pip install -r requirements.txt")
        return None
    schema = load_json(SCHEMA_PATH)
    return jsonschema.Draft202012Validator(schema)


def select_cases(all_cases: Iterable[dict], wanted: list[str]) -> list[dict]:
    cases = [c for c in all_cases if c.get("case_id") and not is_todo(c["case_id"])]
    if not wanted:
        return cases
    by_id = {c["case_id"]: c for c in cases}
    missing = [w for w in wanted if w not in by_id]
    if missing:
        sys.exit(f"unknown case id(s): {', '.join(missing)}")
    return [by_id[w] for w in wanted]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cases", type=Path, default=HERE / "cases.yaml")
    parser.add_argument("--ground-truth", type=Path, default=HERE / "ground_truth")
    parser.add_argument("--runs-dir", type=Path, default=HERE / "runs")
    parser.add_argument("--out", type=Path, default=HERE / "reports")
    parser.add_argument("--runner", choices=["offline", "claude-api"], default="offline")
    parser.add_argument("--case", action="append", default=[], dest="case_ids")
    parser.add_argument(
        "--strict-schema",
        action="store_true",
        help="exit non-zero if any run violates dossier.schema.json",
    )
    args = parser.parse_args(argv)

    if not args.cases.exists():
        sys.exit(f"no cases file at {args.cases}")

    spec = load_yaml(args.cases)
    runs_per_case = int((spec.get("defaults") or {}).get("runs_per_case", 3))
    cases = select_cases(spec.get("cases") or [], args.case_ids)
    if not cases:
        sys.exit("no cases to run")

    known_codes, mandatory_codes = load_taxonomy()
    if not known_codes:
        print(
            "note: no liability codes found in references/liability_taxonomy.yaml; "
            "code validation is disabled",
            file=sys.stderr,
        )

    validator = build_validator(args.strict_schema)
    runner: Runner = (
        OfflineRunner(args.runs_dir)
        if args.runner == "offline"
        else ClaudeApiRunner(args.runs_dir)
    )

    results = []
    for case in cases:
        gt_path = args.ground_truth / f"{case['case_id']}.yaml"
        truth = load_yaml(gt_path) if gt_path.exists() else {}
        if not gt_path.exists():
            print(f"note: no ground truth at {gt_path}", file=sys.stderr)
        results.append(
            score_case(
                case,
                truth,
                runner,
                runs_per_case,
                known_codes,
                mandatory_codes,
                validator,
            )
        )

    timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {
        "timestamp": timestamp,
        "runner": args.runner,
        "runs_per_case": runs_per_case,
        "taxonomy_codes_known": len(known_codes),
        "schema_validated": validator is not None,
    }

    out_dir = args.out / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    report = render_report(results, meta)
    (out_dir / "report.md").write_text(report)
    (out_dir / "results.json").write_text(
        json.dumps(results_to_json(results, meta), indent=2) + "\n"
    )

    print(report)
    print(f"\nwrote {out_dir / 'report.md'}")

    if args.strict_schema and any(
        run.schema_errors for r in results for run in r.usable_runs
    ):
        print("\nschema violations present and --strict-schema set", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
