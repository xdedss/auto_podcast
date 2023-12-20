
from PyPDF2 import PdfReader

from typing import Container

from ..audio_builder.segments import *

def extract_text_from_pdf(pdf_path: str, page_range: Container[int]=None):
    reader = PdfReader(pdf_path)
    # print(len(reader.pages))
    for i, page in enumerate(reader.pages):
        if (page_range is not None and i not in page_range):
            continue
        yield page.extract_text()

async def plain_pdf_gen(pdf_path: str, voice: str, page_range: Container[int]=None):
    for page in extract_text_from_pdf(pdf_path, page_range):
        for line in page.split('\n'):
            if (line.strip() == ''):
                # new paragraph
                yield WhiteSpace(1.0)
            else:
                yield TextSegment(
                    line.strip(),
                    voice,
                )

