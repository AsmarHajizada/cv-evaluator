import asyncio
from pathlib import Path
from typing import Annotated, get_args

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .extraction import OcrMode, extract_cv_file
from .job_fetch import JobFetchError, fetch_job_posting
from .pipeline import Evaluator
from .schemas import Report
from .settings import Settings

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()

LEVEL_STYLE = {"supported": "green", "partial": "yellow", "missing": "red"}
ExistingFile = Annotated[Path, typer.Argument(exists=True, dir_okay=False)]


def _ocr_mode(value: str | None, settings: Settings) -> OcrMode:
    if value is None:
        return settings.ocr
    if value not in get_args(OcrMode):
        raise typer.BadParameter(f"--ocr must be one of {get_args(OcrMode)}")
    return value  # type: ignore[return-value]


@app.command()
def extract(cv: ExistingFile, ocr: Annotated[str | None, typer.Option()] = None) -> None:
    """Show the passages extracted from a CV."""
    console.print(extract_cv_file(cv, _ocr_mode(ocr, Settings())).render_for_prompt())


@app.command()
def evaluate(
    cv: ExistingFile,
    job: Annotated[str, typer.Argument(help="Job description file, or a link to the posting")],
    model: Annotated[str | None, typer.Option(help="PydanticAI model string")] = None,
    ocr: Annotated[str | None, typer.Option(help="auto | always | never")] = None,
    json_out: Annotated[Path | None, typer.Option("--json", help="Write report JSON here")] = None,
) -> None:
    """Evaluate a CV against a job description."""
    load_dotenv()
    settings = Settings()
    job_description = _read_job(job)
    with console.status("Extracting CV…"):
        document = extract_cv_file(cv, _ocr_mode(ocr, settings))
    with console.status(f"Evaluating with {model or settings.model}…"):
        report = asyncio.run(
            Evaluator(model=model or settings.model).evaluate(document, job_description)
        )
    if json_out:
        json_out.write_text(report.model_dump_json(indent=2))
        console.print(f"Report written to {json_out}")
    print_report(report)


def _read_job(job: str) -> str:
    if job.startswith(("http://", "https://")):
        with console.status("Fetching job posting…"):
            try:
                posting = asyncio.run(fetch_job_posting(job))
            except JobFetchError as e:
                raise typer.BadParameter(str(e), param_hint="JOB") from e
        console.print(f"Job posting: {posting.title or posting.url} [dim]({posting.source})[/dim]")
        return posting.text
    path = Path(job)
    if not path.is_file():
        raise typer.BadParameter(f"'{job}' is not a file or an http(s) link.", param_hint="JOB")
    return path.read_text()


def print_report(report: Report) -> None:
    s = report.score
    console.print(
        Panel(
            f"[bold]{s.score}/100 · {s.band}[/bold]\n"
            f"Must-have: {s.must_have.supported} supported, {s.must_have.partial} partial, "
            f"{s.must_have.missing} missing\n"
            f"Nice-to-have: {s.nice_to_have.supported} supported, {s.nice_to_have.partial} "
            f"partial, {s.nice_to_have.missing} missing\n\n[dim]{s.rubric}[/dim]",
            title=f"Job fit · {report.cv_filename}",
        )
    )

    table = Table(title="Requirements", show_lines=True, expand=True)
    table.add_column("Requirement", ratio=3)
    table.add_column("Evidence", ratio=4)
    table.add_column("Assessment", ratio=4)
    for fit in report.requirements:
        style = LEVEL_STYLE[fit.level]
        importance = "must" if fit.requirement.importance == "must_have" else "nice"
        evidence = "\n".join(f"[dim]{p.id}[/dim] “{p.text}”" for p in fit.evidence) or "-"
        assessment = f"[{style}]{fit.level}[/{style}] {fit.rationale}"
        if fit.suggestion:
            assessment += f"\n[italic]→ {fit.suggestion}[/italic]"
        table.add_row(f"{fit.requirement.text} [dim]({importance})[/dim]", evidence, assessment)
    console.print(table)

    fb = report.feedback
    quality = Table(title="CV quality", show_lines=True, expand=True)
    quality.add_column("Dimension", ratio=1)
    quality.add_column("Feedback", ratio=5)
    for q in fb.quality:
        style = {"strong": "green", "adequate": "yellow", "weak": "red"}[q.rating]
        cites = f" [dim]({', '.join(q.passage_ids)})[/dim]" if q.passage_ids else ""
        quality.add_row(f"{q.dimension} [{style}]{q.rating}[/{style}]", q.comment + cites)
    console.print(quality)

    summary = f"{fb.summary.text}\n\n[dim]{fb.summary.rationale}[/dim]"
    console.print(Panel(summary, title="Suggested summary"))

    passages = {p.id: p for p in report.passages}
    rewrites = Table(title="Suggested rewrites", show_lines=True, expand=True)
    rewrites.add_column("Original", ratio=1)
    rewrites.add_column("Rewritten", ratio=1)
    for r in fb.rewrites:
        rewrites.add_row(
            f"[dim]{r.passage_id} · {r.issue}[/dim]\n{passages[r.passage_id].text}",
            f"{r.rewritten}\n[dim]{r.rationale}[/dim]",
        )
    console.print(rewrites)

    lines = []
    for i, p in enumerate(fb.priorities, start=1):
        refs = ", ".join(p.requirement_ids + p.passage_ids)
        lines.append(f"[bold]{i}. {p.title}[/bold]" + (f" [dim]({refs})[/dim]" if refs else ""))
        lines.append(f"   {p.detail}")
    console.print(Panel("\n".join(lines), title="Before you apply"))

    stages = " · ".join(
        f"{st.name} {st.seconds:.1f}s ({st.input_tokens}→{st.output_tokens} tok)"
        for st in report.meta.stages
    )
    console.print(f"[dim]{report.meta.matcher} · {stages}[/dim]")


@app.command()
def serve(
    port: Annotated[int, typer.Option()] = 8000,
    reload: Annotated[bool, typer.Option(help="Restart on code changes")] = False,
) -> None:
    """Run the HTTP API for the web UI."""
    import uvicorn

    uvicorn.run("cv_eval.api:app", host="127.0.0.1", port=port, reload=reload)


if __name__ == "__main__":
    app()
