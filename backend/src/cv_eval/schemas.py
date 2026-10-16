"""Pydantic models shared by the pipeline, API, and CLI."""

from enum import StrEnum

from pydantic import BaseModel, Field


class PassageKind(StrEnum):
    paragraph = "paragraph"
    bullet = "bullet"
    table_row = "table_row"


class Passage(BaseModel):
    id: str = Field(description="Stable id such as 'P12'.")
    section: str | None = Field(description="Nearest section heading, e.g. 'Experience'.")
    kind: PassageKind
    text: str


class CVDocument(BaseModel):
    filename: str
    passages: list[Passage]
    markdown: str = Field(description="Docling's markdown export, for display.")

    def passage_map(self) -> dict[str, Passage]:
        return {p.id: p for p in self.passages}

    def full_text(self) -> str:
        return "\n".join(p.text for p in self.passages)

    def render_for_prompt(self) -> str:
        """Passages grouped under their section headings, each tagged with its id."""
        lines: list[str] = []
        current: str | None = None
        for p in self.passages:
            if p.section != current:
                current = p.section
                lines.append(f"\n## {current or 'Header'}")
            lines.append(f"[{p.id}] ({p.kind}) {p.text}")
        return "\n".join(lines).strip()


class Importance(StrEnum):
    must_have = "must_have"
    nice_to_have = "nice_to_have"


class RequirementCategory(StrEnum):
    technical_skill = "technical_skill"
    experience = "experience"
    domain_knowledge = "domain_knowledge"
    education = "education"
    certification = "certification"
    soft_skill = "soft_skill"
    other = "other"


class Requirement(BaseModel):
    id: str = Field(description="Assigned by the pipeline, e.g. 'R3'.")
    text: str = Field(description="One atomic, self-contained requirement.")
    category: RequirementCategory
    importance: Importance
    jd_quote: str = Field(description="Verbatim span of the job description it came from.")


class EvidenceLevel(StrEnum):
    supported = "supported"
    partial = "partial"
    missing = "missing"


class Assessment(BaseModel):
    requirement_id: str
    level: EvidenceLevel
    evidence_ids: list[str] = Field(
        description="Passage ids that support the level. Empty only when level is 'missing'."
    )
    rationale: str = Field(description="One or two sentences explaining the level.")
    suggestion: str | None = Field(
        default=None,
        description="How the CV could demonstrate this better, using facts it already has "
        "or asking the candidate for specific missing details. Null if nothing to add.",
    )


class QualityDimension(StrEnum):
    clarity = "clarity"
    relevance = "relevance"
    specificity = "specificity"
    achievements = "achievements"


class Rating(StrEnum):
    strong = "strong"
    adequate = "adequate"
    weak = "weak"


class DimensionFeedback(BaseModel):
    dimension: QualityDimension
    rating: Rating
    comment: str
    passage_ids: list[str] = Field(description="Example passages illustrating the comment.")


class RewriteIssue(StrEnum):
    vague = "vague"
    missing_outcome = "missing_outcome"
    duty_not_achievement = "duty_not_achievement"
    unclear = "unclear"
    buries_relevant_skill = "buries_relevant_skill"


class BulletRewrite(BaseModel):
    passage_id: str
    issue: RewriteIssue
    rewritten: str = Field(
        description="Uses only facts in the CV. Details the candidate must supply go in "
        "[square brackets], e.g. 'cut latency by [X]%'."
    )
    rationale: str


class SummaryRewrite(BaseModel):
    text: str
    rationale: str


class Priority(BaseModel):
    title: str
    detail: str
    requirement_ids: list[str] = Field(default_factory=list)
    passage_ids: list[str] = Field(default_factory=list)


class Feedback(BaseModel):
    quality: list[DimensionFeedback]
    summary: SummaryRewrite
    rewrites: list[BulletRewrite]
    priorities: list[Priority]


class RequirementFit(BaseModel):
    requirement: Requirement
    level: EvidenceLevel
    evidence: list[Passage]
    rationale: str
    suggestion: str | None


class LevelCounts(BaseModel):
    supported: int = 0
    partial: int = 0
    missing: int = 0


class FitScore(BaseModel):
    score: int = Field(ge=0, le=100)
    band: str
    must_have: LevelCounts
    nice_to_have: LevelCounts
    rubric: str


class StageMeta(BaseModel):
    name: str
    seconds: float
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class RunMeta(BaseModel):
    model: str
    matcher: str
    stages: list[StageMeta]


class Report(BaseModel):
    cv_filename: str
    requirements: list[RequirementFit]
    score: FitScore
    feedback: Feedback
    passages: list[Passage]
    meta: RunMeta
