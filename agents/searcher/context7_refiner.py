import os
import json
import logging
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser, JsonOutputParser
from ..prompts.searcher_prompts import REFINE_MIGRATION_JSON_PROMPT

logger = logging.getLogger(__name__)


class Context7Refiner:
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            temperature=0
        )
        self.list_parser = CommaSeparatedListOutputParser()
        self.json_parser = JsonOutputParser()

    async def refine_migration_advice(self, raw_text: str, element: str) -> Dict[str, Any]:
        logger.info(f"Generating JSON advice for {element}...")

        prompt = ChatPromptTemplate.from_template(REFINE_MIGRATION_JSON_PROMPT)

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({"element": element, "raw_text": raw_text})
            content = response.content if hasattr(response, 'content') else str(response)

            result = self._robust_json_extractor(content)

            if not isinstance(result, dict):
                if isinstance(result, list) and len(result) > 0:
                    result = result[0]
                else:
                    raise ValueError("Parsed output is not a dict")

            return result

        except Exception as e:
            logger.error(f"FAIL JSON for {element}: {e}. Content snippet: {str(content)[:100]}...")
            return {
                "status": "Unknown",
                "instruction": "Manual check required (Parsing Failed).",
                "example": {"before": "", "after": ""}
            }

    def _robust_json_extractor(self, text: str) -> Any:
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            start = text.find('{')
            if start == -1:
                return {}

            balance = 0
            end = -1
            for i, char in enumerate(text[start:], start):
                if char == '{':
                    balance += 1
                elif char == '}':
                    balance -= 1
                    if balance == 0:
                        end = i
                        break

            if end != -1:
                json_candidate = text[start: end + 1]
                return json.loads(json_candidate)

        except Exception:
            pass

        try:
            start = text.find('[')
            end = text.rfind(']')
            if start != -1 and end != -1:
                return json.loads(text[start: end + 1])
        except Exception:
            pass

        return {}