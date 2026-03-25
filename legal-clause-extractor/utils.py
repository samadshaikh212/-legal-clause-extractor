import fitz  # PyMuPDF
import re


def extract_text_from_pdf(uploaded_file) -> str:
    """Read PDF bytes and return full plain text."""
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text


def clean_text(text: str) -> str:
    """Remove junk characters, normalize whitespace."""
    text = re.sub(r'\n{3,}', '\n\n', text)       # collapse blank lines
    text = re.sub(r'[ \t]+', ' ', text)           # collapse spaces
    text = re.sub(r'[^\x20-\x7E\n]', '', text)   # strip non-printable
    return text.strip()


def chunk_text(text: str, min_len: int = 80, max_len: int = 1200) -> list[str]:
    """
    Split text into paragraph-level chunks.
    - Splits on double newlines (paragraph breaks)
    - Merges tiny fragments into the previous chunk
    - Cuts oversized chunks at sentence boundaries
    """
    raw_chunks = text.split('\n\n')
    chunks = []
    buffer = ""

    for para in raw_chunks:
        para = para.strip()
        if not para:
            continue

        buffer = (buffer + " " + para).strip() if buffer else para

        if len(buffer) >= min_len:
            # If buffer is too large, split at sentence boundary
            if len(buffer) > max_len:
                sentences = re.split(r'(?<=[.!?])\s+', buffer)
                temp = ""
                for s in sentences:
                    if len(temp) + len(s) > max_len and temp:
                        chunks.append(temp.strip())
                        temp = s
                    else:
                        temp = (temp + " " + s).strip()
                if temp:
                    buffer = temp
                else:
                    buffer = ""
            else:
                chunks.append(buffer)
                buffer = ""

    if buffer:
        chunks.append(buffer)

    return chunks
