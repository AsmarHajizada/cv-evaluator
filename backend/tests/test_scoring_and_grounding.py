from cv_eval.grounding import invented_numbers, is_verbatim
from cv_eval.schemas import (
    Assessment,
    EvidenceLevel,
    Importance,
    Requirement,
    RequirementCategory,
)
from cv_eval.scoring import compute_score


def _req(rid: str, importance: Importance) -> Requirement:
    return Requirement(
        id=rid,
        text=rid,
        category=RequirementCategory.technical_skill,
        importance=importance,
        jd_quote=rid,
    )


def _assess(rid: str, level: EvidenceLevel) -> Assessment:
    evidence = [] if level == EvidenceLevel.missing else ["P1"]
    return Assessment(requirement_id=rid, level=level, evidence_ids=evidence, rationale="")


def test_score_weights_must_haves_double():
    reqs = [_req("R1", Importance.must_have), _req("R2", Importance.nice_to_have)]
    # must-have supported (2 × 1) + nice-to-have missing (1 × 0) = 2 of 3
    score = compute_score(
        reqs, [_assess("R1", EvidenceLevel.supported), _assess("R2", EvidenceLevel.missing)]
    )
    assert score.score == 67
    assert score.band == "Good evidence"
    assert score.must_have.supported == 1
    assert score.nice_to_have.missing == 1


def test_partial_earns_half_credit():
    reqs = [_req("R1", Importance.must_have)]
    score = compute_score(reqs, [_assess("R1", EvidenceLevel.partial)])
    assert score.score == 50
    assert score.band == "Partial evidence"


def test_is_verbatim_ignores_case_whitespace_and_smart_quotes():
    source = "We’re looking for  4+ years of\nPython experience."
    assert is_verbatim("we're looking for 4+ years of python", source)
    assert not is_verbatim("5+ years of Python", source)


def test_invented_numbers_ignores_placeholders_and_known_numbers():
    cv = "Reduced MAPE from 18% to 11% across 1,200 depots."
    assert invented_numbers("Cut error from 18% to 11% for 1200 depots", cv) == set()
    assert invented_numbers("Cut latency by [X]% for [N] users", cv) == set()
    assert invented_numbers("Served 5 million requests per day", cv) == {"5"}
