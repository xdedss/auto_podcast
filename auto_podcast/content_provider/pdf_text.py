
from PyPDF2 import PdfReader

from typing import Container

from ..audio_builder.segments import *

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    print(len(reader.pages))
    text = ''
    for page in reader.pages:
        yield page.extract_text()

async def plain_pdf_gen(pdf_path, voice, page_range: Container[int]=None):
    for i, page in enumerate(extract_text_from_pdf(pdf_path)):
        if (page_range is not None and i not in page_range):
            continue
        for line in page.split('\n'):
            if (line.strip() == ''):
                # new paragraph
                yield WhiteSpace(1.0)
            else:
                yield TextSegment(
                    line.strip(),
                    voice,
                )

