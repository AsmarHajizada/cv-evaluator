import json

import pytest
from fastapi.testclient import TestClient

from cv_eval import api

from .conftest import EXAMPLES
from .test_pipeline import ASSESSMENTS, FEEDBACK, REQUIREMENTS, ScriptedLLM


@pytest.fixture
def client(monkeypatch):
    llm = ScriptedLLM(requirements=[REQUIREMENTS], matching=[ASSESSMENTS], feedback=[FEEDBACK])
    monkeypatch.setattr(api.settings, "model", llm.model)
    monkeypatch.setattr(api, "warm_up", lambda: None)
    with TestClient(api.app) as c:
        yield c


def _post(client, cv_name: str, cv_bytes: bytes, jd: str):
    return client.post(
        "/api/evaluate",
        files={"cv": (cv_name, cv_bytes)},
        data={"job_description": jd},
    )


def test_streams_stages_then_report(client, sample_jd):
    cv = (EXAMPLES / "cv_ml_engineer.md").read_bytes()
    response = _post(client, "cv.md", cv, sample_jd)

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [e.get("stage") for e in events[:-1]] == ["requirements", "matching", "feedback"]
    assert events[-1]["type"] == "report"
    assert events[-1]["report"]["score"]["score"] == 70


def test_rejects_bad_inputs_before_streaming(client, sample_jd):
    assert _post(client, "cv.pages", b"x", sample_jd).status_code == 400
    assert _post(client, "cv.md", b"# CV\n\nPython", "too short").status_code == 422


def test_model_failure_becomes_error_event(client, monkeypatch, sample_jd):
    def boom(messages, info):
        raise RuntimeError("provider unavailable")

    from pydantic_ai.models.function import FunctionModel

    monkeypatch.setattr(api.settings, "model", FunctionModel(boom, model_name="boom"))
    cv = (EXAMPLES / "cv_ml_engineer.md").read_bytes()
    events = [json.loads(line) for line in _post(client, "cv.md", cv, sample_jd).text.splitlines()]
    assert events[-1] == {"type": "error", "message": "provider unavailable"}


def test_job_posting_errors_become_400(client, monkeypatch):
    async def refuse(url):
        raise api.JobFetchError("That link points to a private network address.")

    monkeypatch.setattr(api, "fetch_job_posting", refuse)
    response = client.post("/api/job-posting", json={"url": "http://10.0.0.1"})
    assert response.status_code == 400
    assert response.json() == {"detail": "That link points to a private network address."}
