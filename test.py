
"""
The example shows how to use audio_builder.build_audio
"""


from typing import (
    Any,
    AsyncGenerator,
    Dict
)

import asyncio
import os
import logging
import shutil


from auto_podcast.audio_builder import build_audio
from auto_podcast.audio_builder.segments import (
    TextSegment, WhiteSpace
)
from auto_podcast.content_provider.plain_text import plain_text_gen
from auto_podcast.content_provider.pdf_text import plain_pdf_gen
from auto_podcast.content_provider.pdf_refine import refined_pdf_gen
import auto_podcast.content_provider.pdf_refine

from logger import setup_root_logger

logger = setup_root_logger("my_log_file.log")
logging.getLogger('auto_podcast.audio_builder').setLevel(logging.DEBUG)
logging.getLogger('auto_podcast.content_provider.pdf_refine').setLevel(logging.DEBUG)


TEXT = "Hello World!"
VOICE_EN = "en-GB-SoniaNeural"
VOICE_CN = "zh-CN-XiaoyiNeural"
OUTPUT_FILE = "test.mp3"


# Path to the uploaded PDF file
pdf_path = 'test.pdf'


async def foo_gen():
    for i in range(8):
        yield TextSegment(
            f'{i}234',
            'zh-CN-XiaoyiNeural',
            rate=1.0 + 0.1 * i
        )
    # yield WhiteSpace(10)


async def amain() -> None:
    """Main function"""
    print('start generation')
    await build_audio(foo_gen())
    # await build_audio(plain_text_gen('foo.txt', VOICE_EN))
    # await build_audio(plain_pdf_gen(pdf_path, VOICE_EN, [1, 2]))

    # output_file = await build_audio(refined_pdf_gen(pdf_path, VOICE_EN, range(21, 31)))
    # shutil.copy(output_file, '21-31.mp3')

    # auto_podcast.content_provider.pdf_refine.test()
    # await auto_podcast.content_provider.pdf_refine.atest()
    print('finished')


if __name__ == "__main__":
    
    loop = asyncio.get_event_loop_policy().get_event_loop()
    try:
        loop.run_until_complete(amain())
    finally:
        loop.close()
