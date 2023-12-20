
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


from auto_podcast.audio_builder import build_audio
from auto_podcast.audio_builder.segments import (
    TextSegment, WhiteSpace
)
from auto_podcast.content_provider.plain_text import plain_text_gen
from auto_podcast.content_provider.pdf_text import plain_pdf_gen
from auto_podcast.content_provider.pdf_refine import refined_pdf_gen
import auto_podcast.content_provider.pdf_refine


logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s')
logger = logging.getLogger()

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
    # await build_audio(foo_gen())
    # await build_audio(plain_text_gen('foo.txt', VOICE_EN))
    # await build_audio(plain_pdf_gen(pdf_path, VOICE_EN, [1, 2]))

    await build_audio(refined_pdf_gen(pdf_path, VOICE_EN, [0]))

    # auto_podcast.content_provider.pdf_refine.test()
    # await auto_podcast.content_provider.pdf_refine.atest()


if __name__ == "__main__":
    
    loop = asyncio.get_event_loop_policy().get_event_loop()
    try:
        loop.run_until_complete(amain())
    finally:
        loop.close()

#     a = {
#   "content": "Back in the 1950s, I wrote a series of six derring-do novels about David “Lucky” Starr and his battles against malefactors within the Solar System. Each of the six took place in a different region of the system, and in each case I made use of the astronomical facts—as they were then known.\nNow, more than a quarter-century later, these novels are being published in new editions; but what a quarter-century it has been! More has been learned about the worlds of our Solar System in this last quarter-century than in all the thousands of years that went before.\nDAVID STARR: SPACE RANGER was written in 1951 and at that time, there was still a faint possibility that there were canals on Mars, as had first been reported three-quarters of a century earlier. There was, therefore, a faint possibility that intelligent life existed there, or had existed at one time.\nSince then, though, we have sent probes past Mars and around it to take photographs of its surface, and map the entire planet. In 1976, we even landed small laboratories on the Martian surface to test its soil.\nThere are no canals. There are instead, craters, giant volcanoes and enormous canyons. The atmosphere is only 1 percent as dense as Earth’s and is almost entirely carbon dioxide. There is no clear sign of any life at all upon Mars, and the possibility of advanced life upon it, now or ever, seems nil.\nIf I had written the book today, I would have had to adjust the plot to take all this into account.\nI hope my Gentle Readers enjoy the book anyway, as an adventure story, but please don’t forget that the advance of science can outdate even the most conscientious science-fiction writer and that my astronomical descriptions are no longer accurate in all respects.\nIsaac Asimov",
#   "ending": ""
# }
#     print(a['content'])