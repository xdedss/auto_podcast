

from langchain_core.output_parsers import StrOutputParser, BaseOutputParser

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

    remapping: dict = {}

    def __init__(self, remapping: dict=dict()):
        super().__init__()
        self.remapping = remapping

    @property
    def _type(self) -> str:
        """Return the output parser type for serialization."""
        return "default"

    def parse(self, text: str) -> str:
        """Parse last json."""
        res = find_last_valid_json(text)
        if (res is None):
            return None
        
        if (type(res) == dict and self.remapping is not None):
            for k_from, k_to in self.remapping.items():
                if (k_from in res):
                    v = res[k_from]
                    res[k_to] = v
                    res.pop(k_from)
        return res


