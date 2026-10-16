"""Fetch a job posting and extract its description.

Prefers the page's schema.org JobPosting data, which most job boards include for search
engines; otherwise falls back to trafilatura's main-content extraction.
"""

import html
import ipaddress
import json
import re
import socket
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

import anyio
import httpx
import trafilatura
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from pydantic import BaseModel

MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_TEXT_CHARS = 20_000
MIN_TEXT_CHARS = 200
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; cv-evaluator/0.1)",
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
}
_EXTRA_FIELDS = ["responsibilities", "qualifications", "skills", "experienceRequirements"]
_BLOCK_TAGS = ["p", "div", "section", "ul", "ol", "tr", "h1", "h2", "h3", "h4", "h5", "h6"]


class JobFetchError(ValueError):
    pass


class JobPosting(BaseModel):
    url: str
    title: str | None
    text: str
    source: Literal["json-ld", "page", "text"]
    truncated: bool


async def fetch_job_posting(
    url: str, transport: httpx.AsyncBaseTransport | None = None
) -> JobPosting:
    final_url, body, content_type = await _download(url.strip(), transport)

    if "text/plain" in content_type:
        title, text, source = None, body.strip(), "text"
    elif posting := _find_json_ld_posting(body):
        title, text, source = _posting_title(posting), _posting_text(posting), "json-ld"
    else:
        title, text, source = _main_content(body, final_url)

    if len(text) < MIN_TEXT_CHARS:
        raise JobFetchError(
            "Couldn't find a job description on that page. It may need a login or "
            "JavaScript to load. Paste the text instead."
        )
    if title and title.lower() not in text[:300].lower():
        text = f"{title}\n\n{text}"
    truncated = len(text) > MAX_TEXT_CHARS
    if truncated:
        text = text[:MAX_TEXT_CHARS].rsplit("\n", 1)[0]
    return JobPosting(url=final_url, title=title, text=text, source=source, truncated=truncated)


async def _ensure_public(host: str) -> None:
    """Refuse hosts that resolve to private, loopback, or link-local addresses."""
    try:
        infos = await anyio.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise JobFetchError(f"Couldn't find the site '{host}'.") from e
    for *_, sockaddr in infos:
        address = ipaddress.ip_address(str(sockaddr[0]).split("%")[0])
        if not address.is_global:
            raise JobFetchError("That link points to a private network address.")


async def _download(url: str, transport: httpx.AsyncBaseTransport | None) -> tuple[str, str, str]:
    async with httpx.AsyncClient(
        headers=_HEADERS, timeout=10.0, follow_redirects=False, transport=transport
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise JobFetchError("Enter a link that starts with http:// or https://.")
            await _ensure_public(parsed.hostname)  # checked on every redirect hop

            try:
                async with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers["location"])
                        continue
                    _raise_for_status(response.status_code)
                    content_type = response.headers.get("content-type", "").lower()
                    if "html" not in content_type and "text/plain" not in content_type:
                        raise JobFetchError("That link isn't a web page.")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body += chunk
                        if len(body) > MAX_PAGE_BYTES:
                            raise JobFetchError("That page is too large.")
                    text = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                    return str(response.url), text, content_type
            except httpx.TimeoutException as e:
                raise JobFetchError("The site took too long to respond.") from e
            except httpx.HTTPError as e:
                raise JobFetchError(f"Couldn't load the page ({type(e).__name__}).") from e
    raise JobFetchError("Too many redirects.")


def _raise_for_status(status: int) -> None:
    if status in (401, 403, 429, 999):  # 999: LinkedIn's bot response
        raise JobFetchError(
            "The site refused the request; it may need a login or block automated access. "
            "Paste the text instead."
        )
    if status == 404:
        raise JobFetchError("That page doesn't exist (404). The posting may have closed.")
    if status >= 400:
        raise JobFetchError(f"The site returned an error (HTTP {status}).")


def _find_json_ld_posting(page: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(page, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "", strict=False)
        except json.JSONDecodeError:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                types = node.get("@type")
                types = types if isinstance(types, list) else [types]
                if "JobPosting" in types and isinstance(node.get("description"), str):
                    return node
                if "@graph" in node:
                    stack.append(node["@graph"])
    return None


def _posting_title(posting: dict[str, Any]) -> str | None:
    title = posting.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    org = posting.get("hiringOrganization")
    name = org.get("name") if isinstance(org, dict) else None
    title = html.unescape(title.strip())
    return f"{title} at {name.strip()}" if isinstance(name, str) and name.strip() else title


def _posting_text(posting: dict[str, Any]) -> str:
    parts = [html_to_text(posting["description"])]
    for field in _EXTRA_FIELDS:
        value = posting.get(field)
        if isinstance(value, str) and (extra := html_to_text(value)) and extra not in parts[0]:
            parts.append(extra)
    return "\n\n".join(p for p in parts if p)


def html_to_text(fragment: str) -> str:
    """Convert an HTML fragment to plain text, with list items as '- ' lines."""
    if "&lt;" in fragment and "<" not in fragment:
        fragment = html.unescape(fragment)
    soup = BeautifulSoup(fragment, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for li in soup.find_all("li"):
        li.replace_with(NavigableString(f"\n- {' '.join(li.get_text(' ').split())}\n"))
    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_before(NavigableString("\n"))
        tag.insert_after(NavigableString("\n"))

    out: list[str] = []
    for raw in soup.get_text().splitlines():
        line = re.sub(r"[ \t\xa0]+", " ", raw).strip()
        if not line:
            if out and out[-1]:
                out.append("")
            continue
        if line.startswith("- ") and len(out) >= 2 and not out[-1] and out[-2].startswith("- "):
            out.pop()  # keep consecutive bullets together
        out.append(line)
    return "\n".join(out).strip()


def _main_content(page: str, url: str) -> tuple[str | None, str, Literal["page"]]:
    text = trafilatura.extract(
        page,
        url=url,
        output_format="markdown",
        include_tables=True,
        include_links=False,
        include_images=False,
        include_comments=False,
        favor_recall=True,
    )
    metadata = trafilatura.extract_metadata(page, default_url=url)
    title = metadata.title if metadata and metadata.title else None
    text = (text or "").replace("**", "").strip()  # drop markdown bold
    return title, text, "page"
