

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.runnables import RunnableBranch
from langchain.globals import set_debug

set_debug(True)

import json


def find_last_valid_json(input_string):
    # Find the last occurrence of ']' or '}'
    last_index = max(input_string.rfind(']'), input_string.rfind('}'))

    # If neither ']' nor '}' is found, return None
    if last_index == -1:
        return None

    # Extract the potential JSON string
    for i in range(last_index):
        if (input_string[i] in ['[', '{']):
            potential_json = input_string[i:last_index + 1]

            # Try to parse the string as JSON
            try:
                json_object = json.loads(potential_json)
                return json_object  # Return the JSON object if parsing is successful
            except json.JSONDecodeError:
                pass
    return None  # Return None if parsing fails

class JsonOutputParser(BaseOutputParser):
    """OutputParser that parses LLMResult into json."""

    @property
    def _type(self) -> str:
        """Return the output parser type for serialization."""
        return "default"

    def parse(self, text: str) -> str:
        """Parse last json."""
        res = find_last_valid_json(text)
        if (res is None):
            return None
        return res




chain = (
    PromptTemplate.from_template(
        """Given the user question below, classify it as either being about `Math`, `Physics`, or `Other`.

Respond in strict json format: {"classification": "..."}

<question>
{{question}}
</question>

Answer:""",
    template_format='jinja2'
    )
    | ChatOpenAI(temperature=0)
    | JsonOutputParser()
)


branch = RunnableBranch(
    (
        lambda x: "math" in x["topic"]["classification"].lower(), 
        PromptTemplate.from_template(
            '''Tell me a math puzzle'''
        )
        | ChatOpenAI(temperature=0)
        | StrOutputParser()
    ),
    (
        lambda x: "physics" in x["topic"]["classification"].lower(), 
        PromptTemplate.from_template(
            '''Tell me a joke about physics'''
        )
        | ChatOpenAI(temperature=0)
        | StrOutputParser()
    ),
    PromptTemplate.from_template(
        '''Tell the user that you can not answer this question'''
    )
    | ChatOpenAI(temperature=0)
    | StrOutputParser()
)

print(({'topic': chain} | branch).invoke({'question': 'Why do apples fall'}))
