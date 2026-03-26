import fitz  # PyMuPDF
import re


# ── PDF Reading ───────────────────────────────────────────────────────────────

def extract_text_from_pdf(uploaded_file) -> str:
    """
    Read PDF bytes and return full plain text.
    Uses 'text' layout which preserves legal clause structure best.
    """
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text("text")
    doc.close()
    return full_text


def is_scanned_pdf(uploaded_file) -> bool:
    """
    Detect if a PDF is a scanned image (no text layer).
    Returns True if the PDF has images but almost no extractable text.
    Call this BEFORE extract_text_from_pdf — it resets the file pointer automatically.
    """
    try:
        pdf_bytes = uploaded_file.read()
        uploaded_file.seek(0)  # reset so extract_text_from_pdf can read it again
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        total_text_len = 0
        total_images = 0

        for page in doc:
            total_text_len += len(page.get_text("text").strip())
            total_images += len(page.get_images(full=True))

        doc.close()

        # Scanned = lots of images but barely any text
        if total_images > 0 and total_text_len < 200:
            return True
        return False

    except Exception:
        return False


# ── Text Cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Normalize whitespace without destroying legal content.
    Keeps legal symbols (§ © ® ™), clause numbers, and punctuation intact.
    """
    # Collapse 3+ blank lines down to 2 (preserve paragraph structure)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Collapse multiple spaces/tabs to single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove lines that are just page numbers e.g. "- 3 -" or "3"
    text = re.sub(r'(?m)^\s*[-–]?\s*\d{1,3}\s*[-–]?\s*$', '', text)

    # Remove lines that are just underscores or dashes (signature lines)
    text = re.sub(r'(?m)^\s*[_\-]{4,}\s*$', '', text)

    # Collapse again after removals
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ── Text Chunking ─────────────────────────────────────────────────────────────

# Regex: matches lines that start a new numbered clause
_CLAUSE_START = re.compile(
    r'^(\d+\.[\d\.]*|[A-Z]{1,3}\.|Article\s+\d+|Section\s+\d+|Clause\s+\d+)',
    re.IGNORECASE
)


def _looks_like_clause_start(line: str) -> bool:
    """Return True if a line looks like a numbered clause header."""
    return bool(_CLAUSE_START.match(line.strip()))


def _flush_buffer(buffer: str, chunks: list, max_len: int):
    """
    Append buffer to chunks list.
    If buffer is larger than max_len, split at sentence boundaries first.
    """
    buffer = buffer.strip()
    if not buffer:
        return

    if len(buffer) <= max_len:
        chunks.append(buffer)
        return

    # Split oversized buffer at sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', buffer)
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_len and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip()

    if current:
        chunks.append(current)


def chunk_text(
    text: str,
    min_len: int = 40,
    max_len: int = 2000
) -> list[str]:
    """
    Split contract text into paragraph-level chunks for AI analysis.

    Strategy:
    - Split on double newlines (paragraph breaks)
    - If a line starts a numbered clause, always start a fresh chunk
    - Merge tiny fragments into the previous chunk
    - Split oversized chunks at sentence boundaries

    Args:
        text:    Cleaned contract text from clean_text()
        min_len: Minimum characters for a chunk to be kept (default 40)
        max_len: Maximum characters before a chunk gets split (default 2000)

    Returns:
        List of text chunks ready to send to the AI.
    """
    raw_paragraphs = text.split('\n\n')
    chunks = []
    buffer = ""

    for para in raw_paragraphs:
        para = para.strip()

        if not para:
            continue

        # New numbered clause detected — flush existing buffer first
        if _looks_like_clause_start(para) and buffer:
            _flush_buffer(buffer, chunks, max_len)
            buffer = para
            continue

        # Accumulate into buffer
        buffer = (buffer + "\n\n" + para).strip() if buffer else para

        # Flush if buffer has grown too large
        if len(buffer) > max_len:
            _flush_buffer(buffer, chunks, max_len)
            buffer = ""

    # Flush remaining buffer
    if buffer:
        if len(buffer) >= min_len:
            _flush_buffer(buffer, chunks, max_len)
        elif chunks:
            chunks[-1] = chunks[-1] + " " + buffer  # merge tiny tail

    return chunks


# ── PDF Stats ─────────────────────────────────────────────────────────────────

def get_pdf_stats(text: str) -> dict:
    """
    Return basic stats about the extracted text.
    Used by app.py to show an info row before analysis starts.
    """
    words = len(text.split())
    paragraphs = len([p for p in text.split('\n\n') if p.strip()])
    pages_est = max(1, round(words / 350))  # rough estimate: ~350 words/page

    return {
        "words": words,
        "paragraphs": paragraphs,
        "pages_est": pages_est,
    }
