import asyncio
import logging
import os
import tempfile

import fitz  # pymupdf

logger = logging.getLogger(__name__)


def _convert_sync(epub_path: str) -> str:
    """Blocking epub→PDF conversion using PyMuPDF."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="maman_") as f:
        pdf_path = f.name
    try:
        doc = fitz.open(epub_path)
        doc.save(pdf_path)
        doc.close()
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 1024:
            raise RuntimeError("PyMuPDF produced an empty or missing PDF")
        return pdf_path
    except Exception:
        try:
            os.remove(pdf_path)
        except Exception:
            pass
        raise


async def epub_to_pdf(epub_path: str) -> str:
    """Convert an epub file to PDF. Returns path to PDF temp file."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _convert_sync, epub_path)
