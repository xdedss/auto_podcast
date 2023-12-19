

from ..audio_builder.segments import *

async def plain_text_gen(text_file_name, voice):
    ''' Simply read out given text file with given voice, line by line '''
    with open(text_file_name, 'r', encoding='utf-8') as f:
        while (True):
            line = f.readline()
            if (line == ''):
                # end of file
                break
            if (line.strip() == ''):
                # new paragraph
                yield WhiteSpace(1.0)
            else:
                yield TextSegment(
                    line.strip(),
                    voice,
                )

