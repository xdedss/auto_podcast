


from typing import Generator, AsyncGenerator, Any, Tuple, List, Container
import jsonschema
import logging
import json
import os
import re
from collections import deque

import langchain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import ConfigurableField
from langchain.globals import set_debug
from .llm_utils import JsonOutputParser
from . import simple_caching
from ..audio_builder.segments import *




def is_quotation_mark(char) -> bool:
    # List of unicode quotation marks, from https://hexdocs.pm/ex_unicode/Unicode.Category.QuoteMarks.html
    quotation_marks = [
        "\u0022", "\u0027", "\u00AB", "\u00BB",
        "\u2018", "\u2019", "\u201A", "\u201B",
        "\u201C", "\u201D", "\u201E", "\u201F",
        "\u2039", "\u203A", "\u2E42",
        "\u275B", "\u275C", "\u275D", "\u275E",
        "\u1F676", "\u1F677", "\u1F678",
        "\u2826", "\u2834",
        "\u300C", "\u300D", "\u300E", "\u300F",
        "\u301D", "\u301E", "\u301F",
        "\uFE41", "\uFE42", "\uFE43", "\uFE44",
        "\uFF02", "\uFF07", "\uFF62", "\uFF63"
    ]
    return char in quotation_marks


def contains_quotation_mark(s: str) -> bool:
    for char in s:
        if is_quotation_mark(char):
            return True
    return False

def remove_single_quotes(text):
    
    # TODO: we don't have to compile re every time

    # step1: replace all non-standard single quotes
    quote_marks = [
        "\u2018", "\u2019", "\u201A", "\u201B",
        "\u2039", "\u203A", "\u275B", "\u275C",
        "\uFF07"
    ]
    pattern1 = re.compile(r'\b(?:' + '|'.join(re.escape(m) for m in quote_marks) + r')\b', re.IGNORECASE)
    text = re.sub(pattern1, "'", text)

    # step2 remove all abbreviations with single quotes
    abbreviations = [
        "I'm", "'s", "'re", "n't",
        "I'd", "he'd", "she'd", "it'd", "you'd", "we'd", "they'd",
        "who'd", "what'd", "that'd",
        "'ve", "'ll",
        "o'clock", "rock 'n' roll", "'nuff",
        "ne'er-do-well", "'tis",
    ]
    pattern2 = re.compile(r'\b(?:' + '|'.join(re.escape(abbreviation) for abbreviation in abbreviations) + r')\b', re.IGNORECASE)
    text = re.sub(pattern2, '', text)

    return text

def has_conversation(s: str) -> bool:
    ''' checks if there are quotation marks. exclude "don't" "won't" etc. '''
    s = remove_single_quotes(s)
    return contains_quotation_mark(s)

async def get_annotated_lines(context_lines: List[str], batch_lines: List[str]):
    '''
    returns [{"character": "xxx", "text": "xxxxx"}, ...]
    '''
    #  TODO: implement this with
    res = []
    for line in batch_lines:
        res.append({
            'character': 'foo',
            'text': line,
        })
    return res

def determine_voice(char_name: str) -> str:
    return 'foo'

NARRATOR_VOICE = 'en-GB-SoniaNeural'


async def inference_voice(
        line_iter: AsyncGenerator[str, None], 
        *, 
        batch_size: int=10, 
        context_size: int=10
        ):
    '''
    line_iter: generator that produces lines
    batch_size: how many lines should be batched into one LLM request
    context_size: how many lines should be cached as context
    '''

    # context_queue = deque(maxlen=context_size)
    context_queue_annotated = deque(maxlen=context_size)
    conversation_batch = []

    async for line in line_iter:
        line_has_conversation = has_conversation(line)
        process_batch = False
        if line_has_conversation:
            # add to batch
            conversation_batch.append(line)
            if (len(conversation_batch) >= batch_size):
                process_batch = True
        else:
            # process pending lines if any
            if (len(conversation_batch) > 0):
                process_batch = True

        # handle previously batched lines
        if (process_batch):
            annotated_lines = await get_annotated_lines(context_queue_annotated, conversation_batch)
            # add new lines to cache
            for annotated_dict in annotated_lines:
                # add to context
                if (annotated_dict['character'] is None):
                    # this part is not a conversation
                    yield TextSegment(
                        annotated_dict['text'],
                        NARRATOR_VOICE,
                    )
                    context_queue_annotated.append(f'{annotated_dict["text"]}')
                else:
                    # conversation, annotated
                    yield TextSegment(
                        annotated_dict['text'],
                        determine_voice(annotated_dict['character']),
                    )
                    context_queue_annotated.append(f'{annotated_dict["character"]}: “{annotated_dict["text"]}”')
            conversation_batch.clear()

        # finally process current line
        if (not line_has_conversation):
            # use narrator voice for this line
            yield TextSegment(
                line,
                NARRATOR_VOICE,
            )
            context_queue_annotated.append(line) # enqueue


async def atest():

    async def foo_gen():
        yield "David runs towards the desk, and sat down beside an old man."
        yield "Because he know that he’ll help him"
        yield '"What are you doing?"'
        yield '"Just hanging around" says the old man'
        yield '"how is the weather today?"'
        yield '"It\'s been rainy since this afternoon."'
        yield '"Oh no!" "What?" "I forgot to bring my umbrella"'
        yield '"You can have mine" "Really? Thanks"'
        yield '"Good luck!"'
        yield '10 minutes later, david saw Jack.'
        yield '"Lets play the prime number game." suggests david.'
        yield '"Fine, you first" says Jack'
        yield '"Two."'
        yield '"Three." continues Jack.'
        yield '"Five."'
        yield '"Seven."'
        yield '"Eleven."'
        yield '"Thirteen"'
        yield '"Seventeen"'
        yield '"Nineteen"'
        yield '"Twenty three"'
        yield '"Twenty nine"'
        yield '"Thirty one"'
        yield '"Thirty three"'
        yield '"You are wrong!"'
    
    async for item in inference_voice(foo_gen()):
        print(item)

