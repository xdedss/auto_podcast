
"""

Audio Builder

using edge-tts to generate audio

Usage: build_audio(gen())
    gen() is an async generator you implement that provides text segments
    each segment is a TextSegment object or a WhiteSpace object


"""


from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Union,
)

import asyncio
import os, shutil
import subprocess
import logging

import edge_tts

from . import audio_utils
from .segments import (
    TextSegment,
    WhiteSpace,
)

logger = logging.getLogger(__name__)



def float_to_percent(f: float):
    ''' convert to edge-tts format

    1.1 -> "+10%"

    0.9 -> "-10%"
    '''
    assert f > 0
    d = f - 1
    if (d >= 0):
        return f'+{round(d * 100)}%'
    else:
        return f'-{round(-d * 100)}%'



async def build_whitespace(temp_file: str, segment: WhiteSpace):
    audio_utils.make_empty_mp3(temp_file, segment.time)

async def build_audio_segment(temp_file: str, segment: TextSegment):
    ''' generate one segment with edge-tts. remove whitespace '''
    rate_str = float_to_percent(segment.rate)
    volume_str = float_to_percent(segment.volume)
    communicate = edge_tts.Communicate(segment.text, segment.voice, rate=rate_str, volume=volume_str)
    with open(temp_file, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
    # remove whitespace
    audio_utils.trim_mp3(temp_file, temp_file)



async def build_audio(gen: AsyncGenerator[Union[TextSegment, WhiteSpace], None], temp_dir: str='./temp'):
    ''' build audio by generator output
    '''
    if (os.path.exists(temp_dir)):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    seg_count = 0
    paths_file = os.path.join(temp_dir, 'paths.txt')
    output_file = os.path.join(temp_dir, 'out.mp3')
    
    with open(paths_file, 'w') as paths_f:

        async for segment in gen:

            fname = os.path.join(temp_dir, f'{seg_count:04d}.mp3')
            logger.debug(f'Got segment from generator: {segment}')
            logger.debug(f'Destination: {fname}')

            if (isinstance(segment, TextSegment)):
                await build_audio_segment(fname, segment)
            elif (isinstance(segment, WhiteSpace)):
                await build_whitespace(fname, segment)
            else:
                logger.warning(f'Not a valid segment, ignoring: {segment}')
                continue

            paths_f.write(f"file '{os.path.abspath(fname)}'\n")
            seg_count += 1
    
    logger.debug('Start ffmpeg merging')
    cmd = f'ffmpeg -f concat -safe 0 -i {paths_file} -c copy {output_file}'
    logger.debug(cmd)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
    ret = process.wait() # wait til finished
    
    with open(os.path.join(temp_dir, 'ffmpeg.log'), 'w', encoding='utf-8') as ffmpeg_log_f:
        for line in process.stdout:
            ffmpeg_log_f.write(line)
    
    if (process.returncode != 0):
        logger.warning(f'non zero returncode: {process.returncode}')
    
    return output_file


