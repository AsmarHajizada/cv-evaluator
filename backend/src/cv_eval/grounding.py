"""Checks that model output stays tied to the source text."""

import re

_PLACEHOLDER = re.compile(r"\[[^\]]*\]")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_SPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    return _SPACE.sub(" ", text).strip().lower()


def is_verbatim(quote: str, source: str) -> bool:
    """True if `quote` appears in `source`, ignoring case, whitespace, and smart quotes."""
    return normalize(quote) in normalize(source)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def invented_numbers(text: str, source: str) -> set[str]:
    """Numbers in `text`, ignoring [placeholders], that don't appear in `source`."""
    return _numbers(_PLACEHOLDER.sub("", text)) - _numbers(source)
