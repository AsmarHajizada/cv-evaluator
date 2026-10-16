"""CV + job description -> Report: requirements, matching, feedback, then the score."""

from collections.abc import Callable

from .feedback import generate_feedback
from .llm import ModelLike, model_name
from .matching import LLMMatcher, Matcher
from .requirements import extract_requirements
from .schemas import CVDocument, Report, RequirementFit, RunMeta
from .scoring import compute_score


class Evaluator:
    def __init__(self, model: ModelLike, matcher: Matcher | None = None):
        self.model = model
        self.matcher = matcher or LLMMatcher(model)

    async def evaluate(
        self,
        cv: CVDocument,
        job_description: str,
        on_stage: Callable[[str], None] | None = None,
    ) -> Report:
        """`on_stage` is called with each stage name as it starts."""
        notify = on_stage or (lambda _stage: None)

        notify("requirements")
        requirements, req_meta = await extract_requirements(job_description, self.model)
        notify("matching")
        assessments, match_meta = await self.matcher.assess(requirements, cv)
        notify("feedback")
        feedback, feedback_meta = await generate_feedback(
            cv, job_description, requirements, assessments, self.model
        )

        passages = cv.passage_map()
        by_req = {a.requirement_id: a for a in assessments}
        fits = [
            RequirementFit(
                requirement=r,
                level=by_req[r.id].level,
                evidence=[passages[pid] for pid in by_req[r.id].evidence_ids],
                rationale=by_req[r.id].rationale,
                suggestion=by_req[r.id].suggestion,
            )
            for r in requirements
        ]
        return Report(
            cv_filename=cv.filename,
            requirements=fits,
            score=compute_score(requirements, assessments),
            feedback=feedback,
            passages=cv.passages,
            meta=RunMeta(
                model=model_name(self.model),
                matcher=self.matcher.name,
                stages=[req_meta, match_meta, feedback_meta],
            ),
        )
