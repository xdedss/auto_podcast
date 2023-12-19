
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


from audio_builder import build_audio, TextSegment, WhiteSpace


logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s')
logger = logging.getLogger()

TEXT = "Hello World!"
VOICE_EN = "en-GB-SoniaNeural"
VOICE_CN = "zh-CN-XiaoyiNeural"
OUTPUT_FILE = "test.mp3"


async def plain_text_gen(text_file_name):
    with open(text_file_name, 'r', encoding='utf-8') as f:
        while (True):
            line = f.readline()
            if (line == ''):
                break
            if (line.strip() == ''):
                yield WhiteSpace(1.0)
            else:
                yield TextSegment(
                    line.strip(),
                    VOICE_EN,
                )

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
    # await build_audio(foo_gen())
    await build_audio(plain_text_gen('foo.txt'))


if __name__ == "__main__":
    
    loop = asyncio.get_event_loop_policy().get_event_loop()
    try:
        loop.run_until_complete(amain())
    finally:
        loop.close()