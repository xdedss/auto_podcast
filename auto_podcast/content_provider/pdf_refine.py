
from . import pdf_text

from typing import Generator, Any, Tuple, List, Container
import jsonschema
import logging
import json
import os

import langchain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import ConfigurableField
from langchain.globals import set_debug
from .llm_utils import JsonOutputParser
from . import simple_caching
from ..audio_builder.segments import *

logger = logging.getLogger(__name__)

def iterate_pdf_line(page_iter: Generator[str, Any, None]):
    ''' break pages into lines, + [PAGE SEPARATOR] '''
    for page in page_iter:
        lines = page.strip().split('\n')
        for line in lines:
            yield line
        yield '[PAGE SEPARATOR]'

def iterate_pdf_context(line_iter: Generator[str, Any, None], *, context_size: int=5):
    ''' fron line to tuple (line, context) '''
    context = ['' for _ in range(context_size)] # dummy context before the beginning
    for line in line_iter:
        context.append(line)
        if (len(context) > context_size * 2): # before + after
            yield (context[context_size], context)
            context = context[1:]
    # last (context_size) lines
    for i in range(context_size):
        context.append('')
        yield (context[context_size], context)
        context = context[1:]



async def llm_judge_line_removal(line: str, context_array: List[str]):
    
    chain = (
        ChatPromptTemplate.from_template(
            """
You are an assistant that goes through a text file line by line and identify the category of lines and the relationship between adjacent lines. Please note that the text file is converted from a PDF file. Therefore, it may contain broken formats, and irrelevant informations. Your goal is to check whether a line should be removed, given the context around it. The guidlines are as follows:
1. We use <br> to represent line breaks in the extracted text.
2. A line is preserved if it is consistent with the context.
3. A line is preserved if it is a part of a paragraph, chapter title or section title.
4. A line is removed if it is inconsistent with the context.
5. A line is removed if it belongs to page header or footer, or page separator. 

Your response should contain you thoughts and reasoning, and finally your answer to the question in strict json format: {"remove": true/false} indicating whether the line should be removed.

Here is the line we want to check:
```
{{ line }}
```

Here is the context before and after the line we want to check, for reference.
```
{{ context }}
```
""".strip(),
        template_format='jinja2'
        )
        | ChatOpenAI(temperature=0).configurable_fields(
            temperature=ConfigurableField(
                id="llm_temperature",
                name="LLM Temperature",
                description="The temperature of the LLM",
            )
        )
        | JsonOutputParser()
    )
    
    answer = None
    temperature = 0.0
    while (answer is None):
        try:
            answer = await chain.with_config({"llm_temperature": temperature}).ainvoke({
                'line': line,
                'context': '\n<br>\n'.join(context_array),
            })
            if (answer is not None):
                # validate {"answer": 1}
                jsonschema.validate(answer, {
                    "type": "object",
                    "properties": {
                        "remove": {"type": "boolean"}
                    },
                    "required": ["remove"]
                })
        except Exception:
            import traceback
            traceback.print_exc()
            answer = None
            temperature = 0.5 # increase temperature
    return answer['remove']

async def llm_judge_line_type(line: str, context_array: List[str]):

    chain = (
        ChatPromptTemplate.from_template(
            """
You are an assistant that goes through a text file line by line and identify the category of lines and the relationship between adjacent lines. Please note that the text file is converted from a PDF file. Therefore, it may contain broken formats, headers, footers and extra line breaks. Your goal is to categorize which type a line of text belongs to, given the context around it. The categories are as follows:
1. The line is a part of the book index or the table of contents.
2. The line is a part of a paragraph and is the beginning of a sentence.
3. The line is a part of a paragraph, but not the beginning of a sentence. It is the continuation of the sentence in the previous line.
4. The line is a chapter title or section title.
5. The line is a part of the header or footer of the pdf page.
6. The line does not belong to any category above.

Your response should contain you thoughts and reasoning, and finally your answer to the question in strict json format: {"answer": ans} where ans is the index number of the category you choose.

Here is the line we want to categorize:
```
{{ line }}
```

Here is the context before and after the line we want to categorize, for reference.
```
{{ context }}
```
""".strip(),
        template_format='jinja2'
        )
        | ChatOpenAI(temperature=0).configurable_fields(
            temperature=ConfigurableField(
                id="llm_temperature",
                name="LLM Temperature",
                description="The temperature of the LLM",
            )
        )
        | JsonOutputParser()
    )
    
    answer = None
    while (answer is None):
        try:
            answer = await chain.with_config({"llm_temperature": 0.7}).ainvoke({
                'line': line,
                'context': '\n'.join(context_array),
            })
            if (answer is not None):
                # validate {"answer": 1}
                jsonschema.validate(answer, {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "integer"
                        }
                    },
                    "required": ["answer"],
                    "additionalProperties": False
                })
        except Exception:
            import traceback
            traceback.print_exc()
            answer = None
    
    return answer['answer']


async def llm_summarize_page(page: str):
    cache_dir = 'cache/llm_summarize_page'
    
    chain = (
        ChatPromptTemplate.from_template(
            """
The following text is from a page of a book. Use one sentence to describe what the page is about.

```
{{ page }}
```
""".strip(),
        template_format='jinja2'
        )
        | ChatOpenAI(temperature=0).configurable_fields(
            temperature=ConfigurableField(
                id="llm_temperature",
                name="LLM Temperature",
                description="The temperature of the LLM",
            )
        )
        | StrOutputParser()
    )
    
    cache_id = str(chain) + page
    cached_result = simple_caching.get_text_cache(cache_dir, identifier=cache_id)
    if (cached_result is not None):
        return json.loads(cached_result)
    
    answer = None
    while (answer is None):
        try:
            answer = await chain.with_config({"llm_temperature": 0.0}).ainvoke({
                'page': page,
            })
        except Exception:
            import traceback
            traceback.print_exc()
            answer = None
    
    logger.info('LLM summarize')
    logger.info(answer)

    simple_caching.save_text_cache(cache_dir, identifier=cache_id, text=json.dumps(answer))
    return answer

def count_non_whitespace_characters(input_string):
    # Use a generator expression to iterate over characters and count non-white space characters
    count = sum(1 for char in input_string if not char.isspace())
    return count

async def llm_format_page_(page_text, last_page_description=None):
    cache_dir = 'cache/llm_format_page'
    ''' 
    Remove bad formats, broken lines etc..
    returns {"content": "...", "ending": "..."} '''

    chain_markdown = (
        ChatPromptTemplate.from_template(
            '''
You are a book editor. You have received a manuscript that contains broken formats and some irrelevant text. Now you are going to turn it into standard markdown format. Please follow these guidelines:
- Remove nonsense characters and page numbers.
- In your formatted markdown, remove inappropriate line breaks within sentences.
- In your formatted markdown, paragraphs should have no indentations.
- If the last paragraph is incomplete, do not try to complete it or add punctuation. It will be continued in the next page.
- Make sure you process the full text that is given to you. Do not miss anything.

{{ insert_fyi }}
Here is the current page you are processing
```
{{ page }}
```'''.strip(),
            template_format='jinja2'
        )
        | ChatOpenAI(temperature=0).configurable_fields(
            temperature=ConfigurableField(
                id="llm_temperature",
                name="LLM Temperature",
                description="The temperature of the LLM",
            )
        )
        | StrOutputParser()
    )
    
#     chain_json = (
#         ChatPromptTemplate.from_template(
#             '''
# You are a book editor. You have received a page of manuscript in markdown. Now you are going to split it into two parts and turn it into a json. Please follow these guidelines:
# - The json should be in strict format like {"content": "...", "ending": "..."}
# - The "content" is used to put the majority of the manuscript.
# - The "ending" string is for the last paragraph. Usually the last paragraph is incomplete and is to be continued in the next page. Therefore, do not put them into "content". Put them into "ending" for later analysis.
# - Make sure you process the full text that is given to you. Do not miss anything.

# Here is the current page you are processing
# ```
# {{ page }}
# ```'''.strip(),
#             template_format='jinja2'
#         )
#         | ChatOpenAI(temperature=0).configurable_fields(
#             temperature=ConfigurableField(
#                 id="llm_temperature",
#                 name="LLM Temperature",
#                 description="The temperature of the LLM",
#             )
#         )
#         | JsonOutputParser()
#     )

    
    chain_json = (
        # ChatPromptTemplate.from_messages([
        #     ("system", "You are a helpful assistant"),
        #     ("human", "Hello, how are you doing?"),
        #     ("ai", "I'm doing well, thanks!"),
        #     ("human", "{user_input}"),
        # ])
        ChatPromptTemplate.from_template(
            # "Firstly, tell me where you are planning to make the split." is very important!!
            '''
You are an AI assisstant thet splits long text into two parts. You have received a long text in markdown. Now you are going find the best position to split it and answer with a json. Please follow these guidelines:
- The json should be in strict format like {"split_after": "..."} where "..." is the exact sentence right before the split position.
- Choose the split location carefully. Make the split between the paragraphs where it appears to be a natural break in the text.
- Try to split evenly so that two parts are roughly the same size.
- Make sure you process the full text that is given to you. Do not miss anything.
{{ emphasized_rules }}

Here is the current text you are processing
```
{{ page }}
```

Answer with the strict json format:
'''.strip(),
            template_format='jinja2'
        )
        | ChatOpenAI(temperature=0).configurable_fields(
            temperature=ConfigurableField(
                id="llm_temperature",
                name="LLM Temperature",
                description="The temperature of the LLM",
            )
        )
        # | JsonOutputParser(remapping={'part1': 'content', 'part2': 'ending'})
        | JsonOutputParser()
    )


    cache_id = str(chain_json) + str(chain_markdown) + page_text + str(last_page_description)
    cached_result = simple_caching.get_text_cache(cache_dir, identifier=cache_id)
    if (cached_result is not None):
        return json.loads(cached_result)

    
    
    answer = None
    temperature = 0.0
    emphasized_rules = ''
    while (answer is None):
        try:
            insert_fyi = ''
            if (last_page_description is not None):
                insert_fyi = f'''For your information, here is what the previous page was about:
{repr(last_page_description)}
'''
            page_markdown = await chain_markdown.with_config({"llm_temperature": temperature}).ainvoke({
                'page': page_text,
                'insert_fyi': insert_fyi,
            })
            answer = await chain_json.with_config({"llm_temperature": 0.7}).ainvoke({
                'page': page_markdown,
                'emphasized_rules': emphasized_rules,
            })
            if (answer is None):
                # no json
                set_debug(True)
                logger.info(f'no valid json in LLM response, retry')
                temperature = min(0.8, temperature + 0.2) # increase temperature
                emphasized_rules += '- Answer with strict json format.\n'
                continue
            
            # jsonschema.validate(answer, {
            #     "type": "object",
            #     "properties": {
            #         "content": {"type": "string"},
            #         "ending": {"type": "string"}
            #     },
            #     "required": ["content", "ending"]
            # })
            jsonschema.validate(answer, {
                "type": "object",
                "properties": {
                    "split_after": {"type": "string"},
                },
                "required": ["split_after"]
            })

        except Exception:
            import traceback
            traceback.print_exc()
            answer = None
            temperature = min(0.8, temperature + 0.2) # increase temperature
            emphasized_rules += '- Answer with strict json format.\n'
            continue
        
        logger.debug(f'Original page:')
        logger.debug(page_text)
        logger.debug(f'LLM markdown response {page_markdown}')
        logger.debug(f'LLM json response {answer}')

        if (answer['split_after'] not in page_markdown):
            logger.info(f'invalid split position: {answer["split_after"]}')
            answer = None
            temperature = min(0.8, temperature + 0.2)
            emphasized_rules += '- Make the split_after text brief and explicit.\n'
            continue
        
        split_index = page_markdown.find(answer['split_after']) + len(answer['split_after'])
        answer = {'content': page_markdown[:split_index], 'ending': page_markdown[split_index:]}

        # len_after = count_non_whitespace_characters(answer['content']) + count_non_whitespace_characters(answer['ending'])
        # logger.info(f'LLM format page: {len_before} -> {len_after}')
        # if (len_before - len_after > 40 and len_after / len_before < 0.9):
        #     # too short, something is wrong
        #     logger.info(f'LLM is shrinking the page too much, retry')
        #     answer = None
        #     temperature = min(0.8, temperature + 0.2)
    
    simple_caching.save_text_cache(cache_dir, identifier=cache_id, text=json.dumps(answer))
    return answer


async def llm_format_page(page_text, last_page_description=None):
    cache_dir = 'cache/llm_format_page'
    ''' 
    Remove bad formats, broken lines etc..
    returns {"content": "...", "ending": "..."} '''

    chain_markdown = (
        ChatPromptTemplate.from_template(
            '''
You are a book editor. You have received a manuscript that contains broken formats and some irrelevant text. Now you are going to turn it into standard markdown format. Please follow these guidelines:
- Remove nonsense characters and page numbers.
- In your formatted markdown, remove inappropriate line breaks within sentences.
- In your formatted markdown, paragraphs should have no indentations.
- If the last paragraph is cut off, do not add punctuation.
- Make sure you process the full text that is given to you. Do not miss anything.
{{ emphasized_rules }}
{{ insert_fyi }}
Here is the current page you are processing
```
{{ page }}
```'''.strip(),
            template_format='jinja2'
        )
        | ChatOpenAI(temperature=0).configurable_fields(
            temperature=ConfigurableField(
                id="llm_temperature",
                name="LLM Temperature",
                description="The temperature of the LLM",
            )
        )
        | StrOutputParser()
    )


    cache_id = str(chain_markdown) + page_text + str(last_page_description)
    cached_result = simple_caching.get_text_cache(cache_dir, identifier=cache_id)
    if (cached_result is not None):
        return json.loads(cached_result)

    answer = None
    temperature = 0.0
    emphasized_rules = ''
    max_retries = 5
    num_retries = 0
    while (answer is None):

        num_retries += 1
        if (num_retries > max_retries):
            logger.warning(f'max retries reached, fall back to raw text')
            answer = page_text
            break

        try:
            insert_fyi = ''
            if (last_page_description is not None):
                insert_fyi = f'''For your information, here is what the previous page was about:
{repr(last_page_description)}
'''
            page_markdown = await chain_markdown.with_config({"llm_temperature": temperature}).ainvoke({
                'page': page_text,
                'emphasized_rules': emphasized_rules,
                'insert_fyi': insert_fyi,
            })

            # check text length
            len_before = count_non_whitespace_characters(page_text)
            len_after = count_non_whitespace_characters(page_markdown)
            logger.info(f'LLM format page: {len_before} -> {len_after}')
            if (len_before - len_after > 40 and len_after / len_before < 0.9):
                # too short, something is wrong
                logger.info(f'LLM is shrinking the page too much, retry')
                answer = None
                temperature = min(0.8, temperature + 0.2)
                emphasized_rules += '- Make sure you process the full text that is given to you. Do not miss anything.\n'

            answer = page_markdown

        except Exception:
            import traceback
            traceback.print_exc()
            answer = None
            temperature = min(0.8, temperature + 0.2) # increase temperature
            emphasized_rules += '- Answer with strict json format.\n'
            continue
        
        logger.debug(f'Original page:')
        logger.debug(page_text)
        logger.debug(f'LLM markdown response:')
        logger.debug(answer)

        # now answer is formatted, determine the split position

        num_breaks = answer.count('\n')
        logger.debug(f'Num breaks={num_breaks}')
        def index_for_occurrence(text, c, n):
            gen = (i for i, l in enumerate(text) if l == c)
            for _ in range(n):
                next(gen)
            return next(gen)
        split_index = index_for_occurrence(answer, '\n', num_breaks // 2)
        
        answer = {'content': page_markdown[:split_index], 'ending': page_markdown[split_index:]}
    
    simple_caching.save_text_cache(cache_dir, identifier=cache_id, text=json.dumps(answer))
    return answer



async def iterate_refined_pdf_pages(pdf_path, page_range: Container[int]=None):
    page_cache = ''
    last_page_description = None
    for page in pdf_text.extract_text_from_pdf(pdf_path, page_range):
        page_cache += '\n' + page
        llm_format = await llm_format_page(page_cache, last_page_description)
        page_cache = llm_format['ending']
        page_formated = llm_format['content']
        last_page_description = await llm_summarize_page(page_formated)
        yield page_formated
    yield page_cache

async def refined_pdf_gen(pdf_path: str, voice: str, page_range: Container[int]=None):
    async for page in iterate_refined_pdf_pages(pdf_path, page_range):
        logger.info('Refined page')
        logger.info(page)
        for line in page.split('\n'):
            if (line.strip() == ''):
                continue
            else:
                if (line.startswith('#')):
                    yield TextSegment(
                        line.strip().strip('#'),
                        voice,
                        rate = 0.7
                    )
                    yield WhiteSpace(1.0)
                else:
                    yield TextSegment(
                        line.strip(),
                        voice,
                    )
                    yield WhiteSpace(1.0)

async def atest():
    # set_debug(True)
    logger.setLevel(logging.DEBUG)

    # agen = iterate_line_type_llm(
    #     iterate_pdf_context(
    #         iterate_pdf_line(
    #             pdf_text.extract_text_from_pdf('test.pdf', page_range=[3, 5])
    #         ),
    #         context_size=5
    #     )
    # )
    # with open('log.txt', 'w', encoding='utf-8') as f:
    #     async for line, line_type in agen:
    #         f.write(f'[{line_type}] {line}\n')
    #         f.flush()



    # pages = pdf_text.extract_text_from_pdf('test.pdf', range(5))
    # import os
    # os.makedirs('pages', exist_ok=True)
    # page_cache = ''
    # last_page_description = None
    # for i, page in enumerate(pages):
    #     page_cache += '\n' + page
    #     llm_format = await llm_format_page(page_cache, last_page_description)
    #     page_cache = llm_format['ending']
    #     page_formated = llm_format['content']
    #     last_page_description = await llm_summarize_page(page_formated)
    #     logger.info('LLM summarize')
    #     logger.info(last_page_description)
    #     with open(os.path.join('pages', f'{i:04d}.txt'), 'w', encoding='utf-8') as f:
    #         f.write(page)
    #     with open(os.path.join('pages', f'{i:04d}_format.txt'), 'w', encoding='utf-8') as f:
    #         f.write(page_formated)

    import os
    os.makedirs('pages', exist_ok=True)
    i = 0
    page_range = range(15, 21)
    async for page in (iterate_refined_pdf_pages('test.pdf', page_range)):
        set_debug(False) # reset
        page_i = f'{page_range[i]:04d}' if i < len(page_range) else f'{page_range[-1]:04d}_final'
        with open(os.path.join('pages', f'{page_i}_format.txt'), 'w', encoding='utf-8') as f:
            f.write(page)
        i += 1

def test():
    def page_iter():
        yield '''
111
222
333
'''
        yield '''
444
5556
666
'''
        yield '''
777
8
9
'''
    print(list(iterate_pdf_context(iterate_pdf_line(page_iter()))))
