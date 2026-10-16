"""Assess each job requirement against the CV passages."""

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext

from .llm import ModelLike, model_name, run_stage
from .rubric import EVIDENCE_RUBRIC
from .schemas import Assessment, CVDocument, EvidenceLevel, Requirement, StageMeta


class Matcher(Protocol):
    name: str

    async def assess(
        self, requirements: list[Requirement], cv: CVDocument
    ) -> tuple[list[Assessment], StageMeta]: ...


def render_requirements(requirements: list[Requirement]) -> str:
    return "\n".join(f"[{r.id}] ({r.importance}, {r.category}) {r.text}" for r in requirements)


def assessment_problems(
    assessments: list[Assessment], requirement_ids: list[str], passage_ids: set[str]
) -> list[str]:
    """Problems with a matcher's output; empty when the output is valid."""
    problems = []
    seen = [a.requirement_id for a in assessments]
    if missing := [r for r in requirement_ids if r not in seen]:
        problems.append(f"Not assessed: {', '.join(missing)}.")
    if extra := sorted({r for r in seen if r not in requirement_ids}):
        problems.append(f"Unknown requirement ids: {', '.join(extra)}.")
    if dupes := sorted({r for r in seen if seen.count(r) > 1}):
        problems.append(f"Assessed more than once: {', '.join(dupes)}.")
    for a in assessments:
        if unknown := [e for e in a.evidence_ids if e not in passage_ids]:
            problems.append(f"{a.requirement_id} cites passages that do not exist: {unknown}.")
        if a.level == EvidenceLevel.missing and a.evidence_ids:
            problems.append(f"{a.requirement_id} is 'missing' but cites evidence.")
        if a.level != EvidenceLevel.missing and not a.evidence_ids:
            problems.append(f"{a.requirement_id} is '{a.level}' but cites no evidence.")
    return problems


INSTRUCTIONS = f"""\
You assess how well a CV demonstrates each requirement of a job.

{EVIDENCE_RUBRIC}

How to work:
- The CV is split into passages tagged [P<n>], grouped under their section headings.
  Use the section to tell a skills-list mention from described work.
- Assess every requirement exactly once, in the order given.
- evidence_ids: the 1-3 passages that best justify the level. None for 'missing'.
- rationale: one or two sentences on what the cited passages show or lack.
- suggestion: one concrete way the CV could demonstrate the requirement better: surface
  facts already in the CV, or ask the candidate for specific details (scale, duration,
  outcome) if they have them. Never suggest claiming experience the CV does not show.
  Null when the evidence is already strong.\
"""


class AssessmentList(BaseModel):
    assessments: list[Assessment]


@dataclass
class MatchDeps:
    requirement_ids: list[str]
    passage_ids: set[str]


match_agent = Agent(
    output_type=AssessmentList,
    deps_type=MatchDeps,
    instructions=INSTRUCTIONS,
    retries=2,
    name="matcher",
)


@match_agent.output_validator
def _check_assessments(ctx: RunContext[MatchDeps], output: AssessmentList) -> AssessmentList:
    problems = assessment_problems(
        output.assessments, ctx.deps.requirement_ids, ctx.deps.passage_ids
    )
    if problems:
        listed = "\n- ".join(problems)
        raise ModelRetry(f"Fix these problems and return all assessments:\n- {listed}")
    order = {r: i for i, r in enumerate(ctx.deps.requirement_ids)}
    output.assessments.sort(key=lambda a: order[a.requirement_id])
    return output


class LLMMatcher:
    """Judges all requirements in one structured call."""

    def __init__(self, model: ModelLike):
        self.model = model
        self.name = f"llm:{model_name(model)}"

    async def assess(
        self, requirements: list[Requirement], cv: CVDocument
    ) -> tuple[list[Assessment], StageMeta]:
        prompt = (
            f"<requirements>\n{render_requirements(requirements)}\n</requirements>\n\n"
            f"<cv>\n{cv.render_for_prompt()}\n</cv>"
        )
        deps = MatchDeps(
            requirement_ids=[r.id for r in requirements],
            passage_ids={p.id for p in cv.passages},
        )
        output, meta = await run_stage(
            match_agent, prompt, model=self.model, deps=deps, stage="matching"
        )
        return output.assessments, meta
