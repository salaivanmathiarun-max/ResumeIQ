import io
from pathlib import Path
import re
from typing import Tuple
import zipfile

import docx
import fitz  # PyMuPDF

from app.core.config import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE_BYTES


class DocumentProcessingError(Exception):
    """Base exception for document processing errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class FileOversizedError(DocumentProcessingError):
    def __init__(self, message: str = "File size exceeds maximum allowed limit of 5 MB"):
        super().__init__(message, status_code=413)


class UnsupportedFileTypeError(DocumentProcessingError):
    def __init__(self, message: str = "Unsupported file type. Only PDF and DOCX files are allowed."):
        super().__init__(message, status_code=400)


class EmptyDocumentError(DocumentProcessingError):
    def __init__(self, message: str = "The document is empty or contains no extractable text."):
        super().__init__(message, status_code=400)


class CorruptDocumentError(DocumentProcessingError):
    def __init__(self, message: str = "The document is corrupt or could not be parsed."):
        super().__init__(message, status_code=400)


COMMON_HYPHENATED_WORDS = {
    "cross-functional", "full-stack", "end-to-end", "real-time", "open-source",
    "object-oriented", "self-motivated", "multi-threaded", "client-side",
    "server-side", "user-facing", "cost-effective", "high-performance",
    "data-driven", "test-driven", "machine-learning", "front-end", "back-end",
    "cloud-native", "large-scale", "results-driven", "well-established",
    "fast-paced", "mission-critical", "cutting-edge"
}


def normalize_text(raw_text: str) -> str:
    """
    Normalizes extracted resume text for enhanced readability without modifying factual data:
    1. Removes line-break hyphenation while preserving genuine compound words.
    2. Unwraps hard-wrapped paragraph lines into continuous sentences.
    3. Preserves headings, bullet points, and section layout.
    """
    if not raw_text:
        return ""

    # Normalize line endings and non-breaking characters
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u00ad", "")

    # De-hyphenate line-wrap hyphens
    def replace_hyphen(match: re.Match) -> str:
        part1 = match.group(1)
        part2 = match.group(2)
        combined = f"{part1.lower()}-{part2.lower()}"
        if combined in COMMON_HYPHENATED_WORDS:
            return f"{part1}-{part2}"
        return f"{part1}{part2}"

    text = re.sub(r"([A-Za-z]+)-\n\s*([A-Za-z]+)", replace_hyphen, text)

    # Normalize paragraph blocks
    paragraphs = text.split("\n\n")
    normalized_paragraphs = []

    bullet_regex = re.compile(r"^(?:[•\-\*·–—]|\d+[\.\)])\s+")
    heading_regex = re.compile(r"^(?:[A-Z\s]{2,30}:?|[A-Za-z\s]{2,25}:)$")

    for para in paragraphs:
        lines = [line.strip() for line in para.split("\n") if line.strip()]
        if not lines:
            continue
        merged_lines = []
        curr_line = ""

        for line in lines:
            is_bullet = bool(bullet_regex.match(line))
            is_heading = bool(heading_regex.match(line)) and len(line) < 40
            is_short_title = len(line) <= 40 and not line.endswith((",", ";")) and not is_bullet

            if is_bullet or is_heading:
                if curr_line:
                    merged_lines.append(curr_line)
                curr_line = line
            elif is_short_title and (not curr_line or len(curr_line) <= 40 or curr_line.endswith((".", ":", "!", "?"))):
                if curr_line:
                    merged_lines.append(curr_line)
                curr_line = line
            else:
                if not curr_line:
                    curr_line = line
                elif curr_line.endswith((".", ":", "!", "?")):
                    merged_lines.append(curr_line)
                    curr_line = line
                else:
                    curr_line += " " + line

        if curr_line:
            merged_lines.append(curr_line)

        normalized_paragraphs.append("\n".join(merged_lines))

    return "\n\n".join(normalized_paragraphs).strip()


def validate_file_content(content: bytes, filename: str) -> str:
    """
    Validates file size, extension, and binary content signature.
    Returns normalized extension: '.pdf' or '.docx'.
    """
    if len(content) == 0:
        raise EmptyDocumentError("The uploaded file is empty (0 bytes).")

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileOversizedError(
            f"File size ({len(content)} bytes) exceeds maximum limit of {MAX_FILE_SIZE_BYTES} bytes (5 MB)."
        )

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file extension '{ext}'. Only .pdf and .docx files are permitted."
        )

    if ext == ".pdf":
        # PDF magic bytes check (%PDF-) within the initial segment
        if not (content.startswith(b"%PDF-") or b"%PDF-" in content[:1024]):
            raise UnsupportedFileTypeError(
                "Invalid PDF file. The file content does not match a valid PDF header."
            )
    elif ext == ".docx":
        # DOCX is an OpenXML ZIP archive starting with PK\x03\x04
        if not content.startswith(b"PK\x03\x04"):
            raise UnsupportedFileTypeError(
                "Invalid DOCX file. The file content does not match an OpenXML archive header."
            )
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Check for critical document content
                namelist = zf.namelist()
                if "word/document.xml" not in namelist:
                    raise UnsupportedFileTypeError(
                        "Invalid DOCX document. Archive does not contain word/document.xml."
                    )
        except zipfile.BadZipFile as e:
            raise CorruptDocumentError(f"Corrupt DOCX archive: {e}")

    return ext


def extract_text_from_pdf(content: bytes) -> str:
    """Extracts text from all pages of a PDF using PyMuPDF (fitz)."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise CorruptDocumentError(f"Failed to parse PDF document: {exc}")

    try:
        if doc.is_encrypted:
            raise CorruptDocumentError("Encrypted or password-protected PDF files are not supported.")

        page_texts = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")
            if text and text.strip():
                page_texts.append(text.strip())

        extracted = "\n\n".join(page_texts).strip()
        if not extracted:
            raise EmptyDocumentError("The PDF document does not contain readable text.")
        return extracted
    finally:
        doc.close()


def extract_text_from_docx(content: bytes) -> str:
    """Extracts text from paragraphs and tables of a DOCX using python-docx."""
    try:
        doc = docx.Document(io.BytesIO(content))
    except Exception as exc:
        raise CorruptDocumentError(f"Failed to parse DOCX document: {exc}")

    sections = []

    # Paragraphs
    for p in doc.paragraphs:
        if p.text and p.text.strip():
            sections.append(p.text.strip())

    # Tables
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
            if row_texts:
                # Deduplicate identical adjacent cells (e.g., from merged cells)
                deduped = []
                for val in row_texts:
                    if not deduped or val != deduped[-1]:
                        deduped.append(val)
                if deduped:
                    sections.append(" | ".join(deduped))

    extracted = "\n\n".join(sections).strip()
    if not extracted:
        raise EmptyDocumentError("The DOCX document does not contain readable text.")
    return extracted


def extract_text(content: bytes, filename: str) -> Tuple[str, str]:
    """
    Validates and extracts plain text from PDF or DOCX file content.
    Returns: (extracted_text, file_type)
    """
    ext = validate_file_content(content, filename)
    file_type = ext.lstrip(".")

    if ext == ".pdf":
        text = extract_text_from_pdf(content)
    elif ext == ".docx":
        text = extract_text_from_docx(content)
    else:
        raise UnsupportedFileTypeError(f"File type {ext} is not supported.")

    return text, file_type
