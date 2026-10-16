"""CV quality feedback, rewrites, and priorities."""

from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext

from .grounding import invented_numbers
from .llm import ModelLike, run_stage
from .matching import render_requirements
from .schemas import (
    Assessment,
    CVDocument,
    Feedback,
    QualityDimension,
    Requirement,
    StageMeta,
)

MAX_REWRITES = 8

INSTRUCTIONS = f"""\
You give a candidate feedback on their CV for one specific job. You have the job
description, the CV split into passages [P<n>], and an assessment of how well the CV
demonstrates each requirement.

Facts rule: use only facts stated in the CV. Never add employers, tools, numbers,
responsibilities, or results that the CV does not contain. When a stronger bullet needs a
detail the CV lacks, put a placeholder in square brackets for the candidate to fill in,
e.g. "reducing latency by [X]%".

1. quality: exactly one entry per dimension, citing example passages.
   - clarity: easy to scan, plain language, one idea per bullet.
   - relevance: what the job needs is prominent; unrelated content is brief.
   - specificity: concrete tools, scope, and context instead of generic statements.
   - achievements: bullets show outcomes and impact, not only duties.
2. summary: a 2-3 sentence professional summary aimed at this job, built from CV facts.
3. rewrites: up to {MAX_REWRITES} passages whose rewrite would most improve the CV for this
   job. Prefer vague bullets, duties without outcomes, and evidence for partially supported
   requirements. Keep the candidate's voice; one bullet stays one bullet.
4. priorities: the five most useful changes before applying, most impactful first. Weigh
   must-have requirements with partial or missing evidence most. Each must be a concrete
   action; cite the requirement and passage ids it concerns. For missing evidence, advise
   adding it only if the candidate genuinely has that experience.\
"""


@dataclass
class FeedbackDeps:
    cv_text: str
    passage_ids: set[str]
    requirement_ids: set[str]


feedback_agent = Agent(
    output_type=Feedback,
    deps_type=FeedbackDeps,
    instructions=INSTRUCTIONS,
    retries=2,
    name="feedback",
)


@feedback_agent.output_validator
def _check_feedback(ctx: RunContext[FeedbackDeps], output: Feedback) -> Feedback:
    deps = ctx.deps
    problems = []

    dims = [q.dimension for q in output.quality]
    if sorted(dims) != sorted(QualityDimension):
        expected = ", ".join(QualityDimension)
        problems.append(f"quality must have exactly one entry for each of: {expected}.")

    cited = [pid for q in output.quality for pid in q.passage_ids]
    cited += [r.passage_id for r in output.rewrites]
    cited += [pid for p in output.priorities for pid in p.passage_ids]
    if unknown := sorted(set(cited) - deps.passage_ids):
        problems.append(f"Unknown passage ids: {unknown}.")
    reqs = {rid for p in output.priorities for rid in p.requirement_ids}
    if unknown := sorted(reqs - deps.requirement_ids):
        problems.append(f"Unknown requirement ids: {unknown}.")

    if len(output.rewrites) > MAX_REWRITES:
        problems.append(f"Return at most {MAX_REWRITES} rewrites.")
    if not 1 <= len(output.priorities) <= 5:
        problems.append("Return between one and five priorities.")

    for label, text in [("summary", output.summary.text)] + [
        (f"rewrite of {r.passage_id}", r.rewritten) for r in output.rewrites
    ]:
        if new := invented_numbers(text, deps.cv_text):
            problems.append(
                f"The {label} contains numbers not in the CV: {sorted(new)}. "
                "Use a [placeholder] instead."
            )

    if problems:
        raise ModelRetry("Fix these problems:\n- " + "\n- ".join(problems))
    return output


def _render_assessments(requirements: list[Requirement], assessments: list[Assessment]) -> str:
    by_req = {a.requirement_id: a for a in assessments}
    lines = []
    for r in requirements:
        a = by_req[r.id]
        cites = f" [{', '.join(a.evidence_ids)}]" if a.evidence_ids else ""
        lines.append(f"[{r.id}] {a.level}{cites}: {a.rationale}")
    return "\n".join(lines)


async def generate_feedback(
    cv: CVDocument,
    job_description: str,
    requirements: list[Requirement],
    assessments: list[Assessment],
    model: ModelLike,
) -> tuple[Feedback, StageMeta]:
    prompt = (
        f"<job_description>\n{job_description.strip()}\n</job_description>\n\n"
        f"<requirements>\n{render_requirements(requirements)}\n</requirements>\n\n"
        f"<assessments>\n{_render_assessments(requirements, assessments)}\n</assessments>\n\n"
        f"<cv>\n{cv.render_for_prompt()}\n</cv>"
    )
    deps = FeedbackDeps(
        cv_text=cv.full_text(),
        passage_ids={p.id for p in cv.passages},
        requirement_ids={r.id for r in requirements},
    )
    return await run_stage(feedback_agent, prompt, model=model, deps=deps, stage="feedback")
