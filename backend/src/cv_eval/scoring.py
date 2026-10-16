from .rubric import BANDS, IMPORTANCE_WEIGHT, LEVEL_CREDIT, SCORING_RUBRIC
from .schemas import Assessment, FitScore, Importance, LevelCounts, Requirement


def compute_score(requirements: list[Requirement], assessments: list[Assessment]) -> FitScore:
    by_req = {a.requirement_id: a for a in assessments}
    counts = {Importance.must_have: LevelCounts(), Importance.nice_to_have: LevelCounts()}
    earned = possible = 0.0

    for req in requirements:
        level = by_req[req.id].level
        weight = IMPORTANCE_WEIGHT[req.importance]
        earned += weight * LEVEL_CREDIT[level]
        possible += weight
        bucket = counts[req.importance]
        setattr(bucket, level.value, getattr(bucket, level.value) + 1)

    score = round(100 * earned / possible) if possible else 0
    band = next(label for minimum, label in BANDS if score >= minimum)
    return FitScore(
        score=score,
        band=band,
        must_have=counts[Importance.must_have],
        nice_to_have=counts[Importance.nice_to_have],
        rubric=SCORING_RUBRIC,
    )
