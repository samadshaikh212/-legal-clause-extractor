import fitz  # PyMuPDF
import re

def extract_text_from_pdf(uploaded_file) -> str:
    """Read PDF bytes and return full plain text."""
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        # 'text' layout preserves the visual structure better for clauses
        full_text += page.get_text("text") 
    doc.close()
    return full_text

def clean_text(text: str) -> str:
    """Normalize whitespace without deleting special legal symbols."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    # Removed the aggressive non-ASCII stripper to keep symbols like § or ©
    return text.strip()

def chunk_text(text: str, min_len: int = 20, max_len: int = 2000) -> list[str]:
    """
    Split text into paragraph-level chunks.
    Lowered min_len to 20 to capture short but important legal headers.
    """
    raw_chunks = text.split('\n\n')
    chunks = []
    
    for para in raw_chunks:
        para = para.strip()
        if len(para) > min_len:
            # If a paragraph is massive, we still split it, but we use a larger 
            # max_len to avoid cutting a single legal sentence in half.
            if len(para) > max_len:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for s in sentences:
                    if len(current_chunk) + len(s) > max_len:
                        chunks.append(current_chunk.strip())
                        current_chunk = s
                    else:
                        current_chunk += " " + s
                if current_chunk:
                    chunks.append(current_chunk.strip())
            else:
                chunks.append(para)
                
    return chunks
