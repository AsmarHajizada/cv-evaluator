import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model

from .schemas import StageMeta

ModelLike = Model | str


def model_name(model: ModelLike) -> str:
    return model if isinstance(model, str) else model.model_name


async def run_stage[DepsT, OutputT](
    agent: Agent[DepsT, OutputT],
    prompt: str,
    *,
    model: ModelLike,
    deps: DepsT,
    stage: str,
    **kwargs: Any,
) -> tuple[OutputT, StageMeta]:
    """Run an agent and record its latency and token usage."""
    start = time.perf_counter()
    result = await agent.run(prompt, model=model, deps=deps, **kwargs)
    usage = result.usage
    meta = StageMeta(
        name=stage,
        seconds=round(time.perf_counter() - start, 3),
        requests=usage.requests,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )
    return result.output, meta
