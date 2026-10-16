"""Convert a CV file into passages with Docling."""

import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Literal

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.group import InlineGroup
from docling_core.types.doc.items.table.table import TableItem
from docling_core.types.doc.items.text import ListItem, SectionHeaderItem, TextItem
from docling_core.types.doc.labels import DocItemLabel
from docling_core.types.io import DocumentStream

from .schemas import CVDocument, Passage, PassageKind

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".txt", ".html"}
OcrMode = Literal["auto", "always", "never"]

# A text-layer PDF CV has thousands of characters; far fewer means it is probably scanned.
_MIN_PDF_CHARS = 200
# Table cells longer than this mean the table is page layout, not tabular data.
_LAYOUT_CELL_CHARS = 200
_SKIP_LABELS = {DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER, DocItemLabel.CAPTION}
_BULLET = re.compile(r"^\s*[•●▪◦‣∙·\-–—*]\s+")
_SPACE = re.compile(r"\s+")


class ExtractionError(ValueError):
    pass


@lru_cache(maxsize=2)
def _converter(ocr: bool) -> DocumentConverter:
    pdf_options = PdfPipelineOptions(do_ocr=ocr, do_table_structure=True)
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.MD, InputFormat.HTML],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)},
    )


def warm_up() -> None:
    """Load the PDF layout models now instead of on the first request."""
    _converter(ocr=False).initialize_pipeline(InputFormat.PDF)


def _convert(data: bytes, name: str, ocr: bool) -> DoclingDocument:
    result = _converter(ocr).convert(DocumentStream(name=name, stream=BytesIO(data)))
    return result.document


def _clean(text: str) -> str:
    return _SPACE.sub(" ", _BULLET.sub("", text)).strip()


def _looks_like_heading(line: str) -> bool:
    if len(line) > 40 or line[-1] in ".,;":
        return False
    return line.isupper() or line.endswith(":")


def _txt_to_markdown(text: str) -> str:
    """Plain-text CVs put one item per line; markdown would merge those into paragraphs."""
    blocks = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _BULLET.match(line):
            blocks.append(f"- {_clean(line)}")
        elif _looks_like_heading(line):
            blocks.append(f"## {line.rstrip(':').title()}")
        else:
            blocks.append(line)
    return "\n\n".join(blocks)


def _table_texts(table: TableItem) -> list[str]:
    rows = []
    for row in table.data.grid:
        cells: list[str] = []
        for cell in row:
            text = _clean(cell.text)
            if text and (not cells or cells[-1] != text):  # merged cells repeat their text
                cells.append(text)
        rows.append(cells)

    if any(len(c) > _LAYOUT_CELL_CHARS for cells in rows for c in cells):
        return [c for cells in rows for c in cells]
    return [" | ".join(cells) for cells in rows if cells]


def passages_from_docling(doc: DoclingDocument) -> list[Passage]:
    passages: list[Passage] = []
    headings: list[tuple[int, str]] = []  # (level, text) stack, e.g. Experience > role
    consumed: set[str] = set()

    def add(text: str, kind: PassageKind) -> None:
        section = " › ".join(h for _, h in headings) or None
        passages.append(Passage(id=f"P{len(passages) + 1}", section=section, kind=kind, text=text))

    for item, _depth in doc.iterate_items(with_groups=True):
        if item.self_ref in consumed:
            continue
        if isinstance(item, InlineGroup):
            # Bold/links split one line into several text items; rejoin them.
            parts = []
            for child, _ in doc.iterate_items(root=item, with_groups=True):
                consumed.add(child.self_ref)
                if isinstance(child, TextItem) and (text := _clean(child.text)):
                    parts.append(text)
            parent = item.parent.resolve(doc) if item.parent else None
            kind = PassageKind.bullet if isinstance(parent, ListItem) else PassageKind.paragraph
            if parts:
                add(" ".join(parts), kind)
            continue
        if isinstance(item, TableItem):
            for text in _table_texts(item):
                add(text, PassageKind.table_row)
            continue
        if not isinstance(item, TextItem) or item.label in _SKIP_LABELS:
            continue
        text = _clean(item.text)
        if not text:
            continue
        if isinstance(item, SectionHeaderItem) and len(text) <= 80:
            while headings and headings[-1][0] >= item.level:
                headings.pop()
            headings.append((item.level, text))
        elif item.label == DocItemLabel.LIST_ITEM:
            add(text, PassageKind.bullet)
        else:
            add(text, PassageKind.paragraph)

    return passages


def extract_cv(data: bytes, filename: str, ocr: OcrMode = "auto") -> CVDocument:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ExtractionError(f"Unsupported file type '{suffix}'. Supported: {supported}.")

    name = filename
    if suffix == ".txt":
        data = _txt_to_markdown(data.decode("utf-8", errors="replace")).encode()
        name = f"{Path(filename).stem}.md"

    doc = _convert(data, name, ocr=ocr == "always")
    passages = passages_from_docling(doc)

    if suffix == ".pdf" and ocr == "auto" and sum(len(p.text) for p in passages) < _MIN_PDF_CHARS:
        doc = _convert(data, name, ocr=True)
        passages = passages_from_docling(doc)

    if not passages:
        raise ExtractionError(f"No text could be extracted from '{filename}'.")
    return CVDocument(filename=filename, passages=passages, markdown=doc.export_to_markdown())


def extract_cv_file(path: str | Path, ocr: OcrMode = "auto") -> CVDocument:
    path = Path(path)
    return extract_cv(path.read_bytes(), path.name, ocr=ocr)
