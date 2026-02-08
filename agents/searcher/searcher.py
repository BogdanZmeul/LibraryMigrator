import os
import logging
import json
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

from ..tools.serena_tool import SerenaTool
from ..tools.context7_tool import Context7Tool
from ..tools.io.json_handlers import save_json_file
from .context7_refiner import Context7Refiner

from agents.prompts.searcher_prompts import SEARCH_USAGES_SYSTEM_PROMPT
from ..prompts.searcher_prompts import DISCOVERY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class DiscoveryResult(BaseModel):
    import_names: List[str] = Field(description="List of package names used in import statements")

class LibraryUsage(BaseModel):
    method_name: str = Field(
        description="The specific method or class called (e.g., 'read_csv', 'DataFrame'). Do not include the alias prefix.")
    code_snippet: str = Field(description="The exact line of code or block where it is used.")
    line_number: Optional[int] = Field(description="Approximate line number if derivable, else 0")


class FileAnalysisResult(BaseModel):
    usages: List[LibraryUsage]


class RepoSearcher:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.serena = SerenaTool(project_path)
        self.context_ai = Context7Tool()
        self.context_refiner = Context7Refiner()

        self.llm = ChatAnthropic(
            model_name="claude-opus-4-6",
            temperature=0,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.parser = PydanticOutputParser(pydantic_object=FileAnalysisResult)

    async def _discover_import_names(self, library: str) -> List[str]:
        logger.info(f"Discovery: Asking LLM for import names of '{library}'...")

        structured_llm = self.llm.with_structured_output(DiscoveryResult)

        try:
            result: DiscoveryResult = await structured_llm.ainvoke([
                SystemMessage(content=DISCOVERY_SYSTEM_PROMPT),
                HumanMessage(content=f"Identify code-level import names for the library: {library}")
            ])

            names = result.import_names
            if library not in names:
                names.append(library)

            return names
        except Exception as e:
            logger.warning(f"Discovery failed: {e}")
            return [library]

    async def execute_full_search(self, library: str, old_version: str, new_version: str):
        logger.info(f"Universal search: {library} ({old_version} -> {new_version})")

        import_names = await self._discover_import_names(library)

        await self.serena.start()

        candidate_files = await self.serena.find_candidate_files(import_names)
        logger.info(f"Serena found {len(candidate_files)} candidate files containing '{import_names}'.")

        raw_usages = []

        for file_path in candidate_files:
            content = await self.serena.read_file(file_path)
            if not content:
                continue

            logger.info(f"Analyzing usages in {file_path} via LLM...")
            file_usages = await self._extract_usages_with_llm(content, library, file_path)

            logger.info(f"LLM found {file_usages} usages in {file_path}.")
            raw_usages.extend(file_usages)

        grouped_methods = {}
        for item in raw_usages:
            name = item.get('method_name', '')

            if name not in grouped_methods:
                grouped_methods[name] = []
            grouped_methods[name].append(item)

        report = []
        method_names = list(grouped_methods.keys())

        for i, method in enumerate(method_names):
            items = grouped_methods[method]
            full_query = f"{library}.{method}"

            logger.info(f"[{i + 1}/{len(method_names)}] Migration analysis for {full_query}...")

            raw_advice = await self.context_ai.get_migration_advice(library, full_query, old_version, new_version)
            advice = await self.context_refiner.refine_migration_advice(raw_advice, full_query)

            if not advice:
                advice = {}

            report.append({
                "pattern_id": i + 1,
                "title": method,
                "status": advice.get("status", "Unknown"),
                "migration_guide": advice.get("instruction", "Manual check required."),
                "occurrence_count": len(items),
                "affected_files": sorted(list(set(x['file'] for x in items))),
                "code_example": items[0]['pattern'] if items else "",
                "migration_example": advice.get("example", {})
            })

        return report

    async def _extract_usages_with_llm(self, file_content: str, library_name: str, file_path: str) -> List[Dict]:

        system_content = SEARCH_USAGES_SYSTEM_PROMPT.format(library_name=library_name)

        user_prompt = f"File: {file_path}\n\nCode Content:\n```\n{file_content}\n```"

        structured_llm = self.llm.with_structured_output(FileAnalysisResult)

        try:
            result = await structured_llm.ainvoke([
                SystemMessage(content=system_content),
                HumanMessage(content=user_prompt)
            ])

            clean_usages = []
            for usage in result.usages:
                clean_usages.append({
                    "file": file_path,
                    "pattern": usage.code_snippet,
                    "method_name": usage.method_name
                })
            return clean_usages

        except Exception as e:
            logger.error(f"LLM Extraction failed for {file_path}: {e}")
            return []


async def searcher_node(state):
    logger.info("Searcher: Starting process...")

    project_path = state.get("project_path", ".")
    usage_path = state.get("usage_path", "usage.json")

    library = state.get("library")
    old_version = state.get("old_version")
    new_version = state.get("new_version")

    if not library or not old_version or not new_version:
        logger.error("Searcher: Missing required parameters in state.")
        return {"status": "error", "usage_path": usage_path}

    searcher = RepoSearcher(project_path)
    usage_data = await searcher.execute_full_search(library, old_version, new_version)

    if usage_data is None:
        usage_data = []

    save_json_file(usage_path, usage_data)
    logger.info(f"Searcher: Saved {len(usage_data)} usage patterns to {usage_path}.")

    return {
        "status": "search_done",
        "usage_path": usage_path
    }