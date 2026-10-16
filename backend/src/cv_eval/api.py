"""HTTP API for the web UI.

POST /api/evaluate streams NDJSON: a {"type": "stage"} event as each stage starts, then
one {"type": "report"} or {"type": "error"} event.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import anyio
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .extraction import ExtractionError, extract_cv, warm_up
from .job_fetch import JobFetchError, JobPosting, fetch_job_posting
from .pipeline import Evaluator
from .schemas import CVDocument
from .settings import Settings

MAX_CV_BYTES = 5 * 1024 * 1024
MIN_JD_CHARS = 50
MAX_JD_CHARS = 20_000

logger = logging.getLogger(__name__)
load_dotenv()
settings = Settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await anyio.to_thread.run_sync(warm_up)
    yield


app = FastAPI(title="CV Evaluator", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.model}


class JobUrl(BaseModel):
    url: str


@app.post("/api/job-posting")
async def job_posting(body: JobUrl) -> JobPosting:
    try:
        return await fetch_job_posting(body.url)
    except JobFetchError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/evaluate")
async def evaluate(cv: UploadFile, job_description: Annotated[str, Form()]) -> StreamingResponse:
    job_description = job_description.strip()
    if len(job_description) < MIN_JD_CHARS:
        raise HTTPException(422, "Paste the full job description.")
    if len(job_description) > MAX_JD_CHARS:
        raise HTTPException(422, f"Job description is too long (max {MAX_JD_CHARS} characters).")

    data = await cv.read(MAX_CV_BYTES + 1)
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(413, "CV file must be under 5 MB.")
    try:
        document = await anyio.to_thread.run_sync(
            extract_cv, data, cv.filename or "cv.pdf", settings.ocr
        )
    except ExtractionError as e:
        raise HTTPException(400, str(e)) from e

    return StreamingResponse(
        _stream_evaluation(document, job_description), media_type="application/x-ndjson"
    )


async def _stream_evaluation(document: CVDocument, job_description: str) -> AsyncIterator[str]:
    events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def run() -> None:
        try:
            report = await Evaluator(model=settings.model).evaluate(
                document,
                job_description,
                on_stage=lambda stage: events.put_nowait({"type": "stage", "stage": stage}),
            )
            await events.put({"type": "report", "report": report.model_dump(mode="json")})
        except Exception as e:
            logger.exception("Evaluation failed")
            await events.put({"type": "error", "message": str(e)[:500] or type(e).__name__})

    task = asyncio.create_task(run())
    try:
        while True:
            event = await events.get()
            yield json.dumps(event) + "\n"
            if event["type"] != "stage":
                break
    finally:
        task.cancel()  # stops the LLM calls if the client disconnects
