"""Pipeline tests driven by a scripted model."""

from collections import Counter

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from cv_eval.pipeline import Evaluator
from cv_eval.schemas import EvidenceLevel

pytestmark = pytest.mark.anyio

# The output tool's schema tells us which stage is calling.
STAGE_KEYS = {"requirements": "requirements", "matching": "assessments", "feedback": "quality"}

REQUIREMENTS = {
    "requirements": [
        {
            "text": "Production model deployment (APIs, containers)",
            "category": "experience",
            "importance": "must_have",
            "jd_quote": "Production model deployment experience (APIs, containers).",
        },
        {
            "text": "Hands-on experience running workloads on Kubernetes",
            "category": "technical_skill",
            "importance": "must_have",
            "jd_quote": "Hands-on experience running workloads on Kubernetes.",
        },
        {
            "text": "Experience with LLMs or retrieval-augmented generation",
            "category": "technical_skill",
            "importance": "nice_to_have",
            "jd_quote": "Experience with LLMs or retrieval-augmented generation.",
        },
    ]
}

ASSESSMENTS = {
    "assessments": [
        {
            "requirement_id": "R1",
            "level": "supported",
            "evidence_ids": ["P5"],
            "rationale": "Deployed a model as a production API with FastAPI and Docker.",
            "suggestion": "Add request volume or uptime if available.",
        },
        {
            "requirement_id": "R2",
            "level": "partial",
            "evidence_ids": ["P16"],
            "rationale": "Kubernetes appears only in the skills list.",
            "suggestion": "If you ran the API on Kubernetes, say so in the Northwind bullet.",
        },
        {
            "requirement_id": "R3",
            "level": "partial",
            "evidence_ids": ["P13"],
            "rationale": "RAG is shown in a personal project, not professional work.",
            "suggestion": None,
        },
    ]
}

FEEDBACK = {
    "quality": [
        {"dimension": d, "rating": "adequate", "comment": "…", "passage_ids": ["P4"]}
        for d in ["clarity", "relevance", "specificity", "achievements"]
    ],
    "summary": {
        "text": "ML engineer who deployed PyTorch forecasting models to production.",
        "rationale": "Leads with the strongest evidence for this role.",
    },
    "rewrites": [
        {
            "passage_id": "P6",
            "issue": "vague",
            "rewritten": "Owned the ML pipeline from ingestion to deployment for [N] models.",
            "rationale": "States scope instead of a duty.",
        }
    ],
    "priorities": [
        {
            "title": "Show Kubernetes in context",
            "detail": "Describe where you ran workloads on Kubernetes, if you did.",
            "requirement_ids": ["R2"],
            "passage_ids": ["P16"],
        }
    ],
}


class ScriptedLLM:
    """Returns the scripted outputs for each stage in turn; the last one repeats."""

    def __init__(self, **scripts: list[dict]):
        self.scripts = scripts
        self.calls: Counter[str] = Counter()
        self.messages: dict[str, list[ModelMessage]] = {}

    def __call__(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool = info.output_tools[0]
        props = tool.parameters_json_schema["properties"]
        stage = next(s for s, key in STAGE_KEYS.items() if key in props)
        outputs = self.scripts[stage]
        output = outputs[min(self.calls[stage], len(outputs) - 1)]
        self.calls[stage] += 1
        self.messages[stage] = messages
        return ModelResponse(parts=[ToolCallPart(tool.name, output)])

    @property
    def model(self) -> FunctionModel:
        return FunctionModel(self, model_name="scripted")


def _retry_text(messages: list[ModelMessage]) -> str:
    parts = [p for m in messages for p in getattr(m, "parts", []) if isinstance(p, RetryPromptPart)]
    return "\n".join(str(p.content) for p in parts)


async def test_report_is_assembled_from_stages(sample_cv, sample_jd):
    llm = ScriptedLLM(requirements=[REQUIREMENTS], matching=[ASSESSMENTS], feedback=[FEEDBACK])
    report = await Evaluator(model=llm.model).evaluate(sample_cv, sample_jd)

    assert [f.requirement.id for f in report.requirements] == ["R1", "R2", "R3"]
    deploy = report.requirements[0]
    assert deploy.level == EvidenceLevel.supported
    assert "production API service" in deploy.evidence[0].text
    assert report.requirements[1].evidence[0].section == "Skills"
    # must: 2×1 + 2×0.5, nice: 1×0.5 → 3.5 / 5
    assert report.score.score == 70
    assert [s.name for s in report.meta.stages] == ["requirements", "matching", "feedback"]
    assert report.meta.matcher == "llm:scripted"


async def test_matcher_retries_on_unknown_passage_and_missing_requirement(sample_cv, sample_jd):
    bad = {
        "assessments": [
            {**ASSESSMENTS["assessments"][0], "evidence_ids": ["P99"]},
            ASSESSMENTS["assessments"][1],
        ]
    }
    llm = ScriptedLLM(requirements=[REQUIREMENTS], matching=[bad, ASSESSMENTS], feedback=[FEEDBACK])
    report = await Evaluator(model=llm.model).evaluate(sample_cv, sample_jd)

    assert llm.calls["matching"] == 2
    retry = _retry_text(llm.messages["matching"])
    assert "P99" in retry and "Not assessed: R3" in retry
    assert len(report.requirements) == 3


async def test_requirement_quotes_must_be_verbatim(sample_cv, sample_jd):
    invented = {"requirements": [{**REQUIREMENTS["requirements"][0], "jd_quote": "10 years of Go"}]}
    llm = ScriptedLLM(
        requirements=[invented, REQUIREMENTS], matching=[ASSESSMENTS], feedback=[FEEDBACK]
    )
    await Evaluator(model=llm.model).evaluate(sample_cv, sample_jd)

    assert llm.calls["requirements"] == 2
    assert "10 years of Go" in _retry_text(llm.messages["requirements"])


async def test_rewrites_cannot_invent_numbers(sample_cv, sample_jd):
    rewrite = {**FEEDBACK["rewrites"][0], "rewritten": "Owned the ML pipeline serving 40 models."}
    llm = ScriptedLLM(
        requirements=[REQUIREMENTS],
        matching=[ASSESSMENTS],
        feedback=[{**FEEDBACK, "rewrites": [rewrite]}, FEEDBACK],
    )
    report = await Evaluator(model=llm.model).evaluate(sample_cv, sample_jd)

    assert llm.calls["feedback"] == 2
    assert "['40']" in _retry_text(llm.messages["feedback"])
    assert "[N]" in report.feedback.rewrites[0].rewritten
