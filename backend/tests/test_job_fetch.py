import json

import httpx
import pytest

from cv_eval import job_fetch
from cv_eval.job_fetch import JobFetchError, fetch_job_posting, html_to_text

pytestmark = pytest.mark.anyio

BULLETS = "".join(f"<li>Requirement number {i} with enough words to count</li>" for i in range(8))
DESCRIPTION = f"<p>About the role</p><p>&nbsp;</p><b>What we need</b><ul>{BULLETS}</ul>"


def _page(json_ld: object | None = None, body: str = "") -> str:
    script = f'<script type="application/ld+json">{json.dumps(json_ld)}</script>' if json_ld else ""
    return f"<html><head><title>Jobs</title>{script}</head><body>{body}</body></html>"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    async def fake_ensure_public(host: str) -> None:
        if host == "internal.test":
            raise JobFetchError("That link points to a private network address.")

    monkeypatch.setattr(job_fetch, "_ensure_public", fake_ensure_public)


def _transport(routes: dict[str, httpx.Response]) -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: routes[str(request.url)])


def _html(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=text, headers={"content-type": "text/html; charset=utf-8"})


def test_html_to_text_keeps_bullets_tight():
    text = html_to_text("<p>Intro</p><ul><li>One</li><li><p>Two</p></li></ul><p>End</p>")
    assert text == "Intro\n\n- One\n- Two\n\nEnd"


def test_html_to_text_handles_entity_escaped_html():
    assert html_to_text("&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;") == "- Python"


async def test_prefers_json_ld_job_posting_inside_graph():
    posting = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "name": "Acme"},
            {
                "@type": "JobPosting",
                "title": "ML Engineer",
                "hiringOrganization": {"name": "Acme"},
                "description": DESCRIPTION,
            },
        ],
    }
    url = "https://jobs.example.com/1"
    page = _page(posting, body="<nav>Other jobs</nav>")
    result = await fetch_job_posting(url, transport=_transport({url: _html(page)}))

    assert result.source == "json-ld"
    assert result.title == "ML Engineer at Acme"
    assert result.text.startswith("ML Engineer at Acme\n\nAbout the role\n\nWhat we need\n\n- ")
    assert "Other jobs" not in result.text


async def test_falls_back_to_main_content():
    paragraphs = "".join(
        f"<p>We need someone with skill {i} who has shipped production systems.</p>"
        for i in range(10)
    )
    url = "https://jobs.example.com/2"
    page = _page(body=f"<article><h1>Data Scientist</h1>{paragraphs}</article>")
    result = await fetch_job_posting(url, transport=_transport({url: _html(page)}))

    assert result.source == "page"
    assert "skill 9" in result.text


async def test_follows_redirects_and_checks_each_hop():
    start, internal = "https://short.example.com/x", "http://internal.test/admin"
    routes = {start: httpx.Response(302, headers={"location": internal})}
    with pytest.raises(JobFetchError, match="private network"):
        await fetch_job_posting(start, transport=_transport(routes))


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (_html("", status=999), "refused"),
        (_html("", status=404), "404"),
        (
            httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}),
            "isn't a web page",
        ),
        (_html(_page(body="<div id='root'></div>")), "Paste the text"),
    ],
)
async def test_unusable_pages_explain_why(response, message):
    url = "https://jobs.example.com/3"
    with pytest.raises(JobFetchError, match=message):
        await fetch_job_posting(url, transport=_transport({url: response}))


async def test_rejects_non_http_links():
    with pytest.raises(JobFetchError, match="http"):
        await fetch_job_posting("file:///etc/passwd")
