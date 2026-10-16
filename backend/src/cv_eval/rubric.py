"""Evidence level definitions (part of the matcher prompt) and the scoring rule."""

from .schemas import EvidenceLevel, Importance

EVIDENCE_RUBRIC = """\
Judge what the CV demonstrates, not what the candidate might know. "missing" means the
CV gives no evidence; it does not mean the candidate lacks the skill.

supported: the CV shows the requirement applied or achieved in a role, project, or
  result, with enough context to be credible (what was done, where, ideally an outcome).
  Years-of-experience requirements are supported when dated roles add up to the amount.
  Degrees and certifications are supported when the credential is listed.

partial: there is evidence, but weaker than the requirement asks for:
  - only listed in a skills or keywords section, with no described use;
  - used in coursework or a side project when professional experience is asked for;
  - a closely related but different tool, method, or domain;
  - less duration, scale, or seniority than required;
  - a vague claim without context ("familiar with", "exposure to");
  - implied by a job title alone, with no described work.

missing: nothing in the CV addresses the requirement.\
"""

LEVEL_CREDIT: dict[EvidenceLevel, float] = {
    EvidenceLevel.supported: 1.0,
    EvidenceLevel.partial: 0.5,
    EvidenceLevel.missing: 0.0,
}

IMPORTANCE_WEIGHT: dict[Importance, int] = {
    Importance.must_have: 2,
    Importance.nice_to_have: 1,
}

# (minimum score, band label), checked top-down.
BANDS: list[tuple[int, str]] = [
    (80, "Strong evidence"),
    (60, "Good evidence"),
    (40, "Partial evidence"),
    (0, "Limited evidence"),
]

SCORING_RUBRIC = """\
Score = weighted average of requirement credit × 100.
Credit: supported = 1, partial = 0.5, missing = 0.
Weight: must-have = 2, nice-to-have = 1.
Bands: 80+ strong, 60-79 good, 40-59 partial, below 40 limited evidence.
The score measures how well the CV demonstrates the requirements, not the candidate.\
"""
