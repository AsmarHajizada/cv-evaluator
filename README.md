# CV Evaluator

Checks a CV against a job description. Each requirement in the job is marked supported,
partial, or missing, with the CV passages that back the decision. The app also rates the
CV's writing, suggests rewrites, and lists the five most useful changes before applying.

The next step is to train a small model for the matching stage and compare it with a
frontier LLM on agreement with human reviewers, consistency, latency, and cost.

## How it works

1. Docling converts the CV (PDF, DOCX, Markdown, HTML, or plain text) into numbered
   passages, each tagged with its section heading.
2. An LLM extracts requirements from the job description and marks each one as
   must-have or nice-to-have.
3. The matcher assesses every requirement against the passages and cites passage ids as
   evidence. A skill that only appears in a skills list counts as partial.
4. An LLM writes the feedback: ratings for clarity, relevance, specificity, and
   achievements, a suggested summary, bullet rewrites, and priorities.
5. The score is calculated from the assessments: supported = 1, partial = 0.5,
   missing = 0, and must-haves count double. See
   [`rubric.py`](backend/src/cv_eval/rubric.py).

Each LLM step validates its output. If the model cites a passage that doesn't exist,
skips a requirement, misquotes the job description, or adds a number to a rewrite that
isn't in the CV, the error is sent back and the model retries.

Job descriptions can also be loaded from a link. The backend reads the page's schema.org
`JobPosting` data when it has any (Greenhouse, Lever, Ashby, Workday, ...) and otherwise
extracts the main content. Pages behind a login, such as most LinkedIn links, need the
text pasted.

## Layout

```
backend/    Python package: pipeline, FastAPI app, CLI (uv)
frontend/   Next.js + shadcn/ui
examples/   Sample CV and job description
```

## Running

Requires [uv](https://docs.astral.sh/uv/), Node 20+, and a Gemini API key.

```bash
cd backend
uv sync
cp ../.env.example .env        # add GOOGLE_API_KEY
uv run cv-eval serve           # API on http://localhost:8000

cd frontend
npm install
npm run dev                    # UI on http://localhost:3000
```

From the command line:

```bash
uv run cv-eval extract ../examples/cv_ml_engineer.pdf
uv run cv-eval evaluate ../examples/cv_ml_engineer.pdf ../examples/jd_ml_engineer.txt
uv run cv-eval evaluate cv.pdf https://jobs.lever.co/company/posting-id --json report.json
```

The first PDF run downloads Docling's layout models. After that a CV converts in well
under a second.

The model is set with `--model` or `CV_EVAL_MODEL` and accepts any PydanticAI model
string (default `google:gemini-3.8-flash`).

## Development

```bash
cd backend
uv run pytest                 # offline; LLM steps use a scripted model
uv run ruff check && uv run ruff format --check
uv run pyright

cd frontend
npm run lint && npm run format:check && npm run build
```

## Roadmap

1. Core pipeline and CLI (done)
2. Web UI (done)
3. Dataset: CV and job pairs, teacher labels from the LLM matcher, a human-reviewed test set
4. Fine-tune a compact model for the matching stage
5. Evaluation: agreement with reviewers, unsupported judgments, consistency, latency, cost
