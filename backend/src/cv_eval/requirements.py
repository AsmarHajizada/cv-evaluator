"""Job description -> atomic requirements."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from .grounding import is_verbatim
from .llm import ModelLike, run_stage
from .schemas import Importance, Requirement, RequirementCategory, StageMeta

INSTRUCTIONS = """\
You extract the requirements a candidate's CV will be judged against from a job description.

Rules:
- Each requirement is atomic: one skill, experience, credential, or capability. Split
  compound lines ("Python and SQL" becomes two requirements).
- Write each requirement as a short, self-contained phrase that makes sense without the
  job description ("4+ years building ML systems in industry", not "the above").
- Keep stated amounts and qualifiers (years, seniority, "hands-on", "production").
- Include capabilities implied by responsibilities only when they are concrete and not
  already covered (e.g. "Deploy models to production").
- Skip company descriptions, benefits, salary, location, and legal boilerplate.
- importance: must_have when the job states it as required or it is central to the
  responsibilities; nice_to_have when marked preferred, a plus, a bonus, or nice to have.
- jd_quote: copy the exact span of the job description the requirement comes from.
- Merge near-duplicates. Return at most 20 requirements, most important first.\
"""


class RequirementDraft(BaseModel):
    text: str
    category: RequirementCategory
    importance: Importance
    jd_quote: str


class RequirementList(BaseModel):
    requirements: list[RequirementDraft] = Field(min_length=1, max_length=25)


requirements_agent = Agent(
    output_type=RequirementList,
    deps_type=str,
    instructions=INSTRUCTIONS,
    retries=2,
    name="requirements",
)


@requirements_agent.output_validator
def _quotes_are_verbatim(ctx: RunContext[str], output: RequirementList) -> RequirementList:
    bad = [r.jd_quote for r in output.requirements if not is_verbatim(r.jd_quote, ctx.deps)]
    if bad:
        listed = "\n".join(f"- {q!r}" for q in bad)
        raise ModelRetry(
            f"These jd_quote values do not appear verbatim in the job description:\n{listed}\n"
            "Copy the exact text span instead."
        )
    return output


async def extract_requirements(
    job_description: str, model: ModelLike
) -> tuple[list[Requirement], StageMeta]:
    prompt = f"<job_description>\n{job_description.strip()}\n</job_description>"
    output, meta = await run_stage(
        requirements_agent, prompt, model=model, deps=job_description, stage="requirements"
    )
    requirements = [
        Requirement(id=f"R{i}", **draft.model_dump())
        for i, draft in enumerate(output.requirements, start=1)
    ]
    return requirements, meta
