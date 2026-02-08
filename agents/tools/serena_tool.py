import logging
import json
import asyncio
from pathlib import Path
from typing import List, Any
from serena.agent import SerenaAgent

logger = logging.getLogger(__name__)


class SerenaTool:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.agent = None

    async def start(self):
        if not self.workspace_path.exists():
            raise FileNotFoundError(f"Path {self.workspace_path} not found!")

        logger.info(f"Launch Serena in the workspace: {self.workspace_path}")
        try:
            self.agent = SerenaAgent()
            self.agent.load_project_from_path_or_name(str(self.workspace_path), autogenerate=True)
            self.agent.activate_project_from_path_or_name(str(self.workspace_path))

            logger.info("Waiting for LSP server initialization...")
            await asyncio.sleep(5)
            logger.info("Serena LSP is ready for analysis.")
        except Exception as e:
            logger.error(f"Error when starting Serena: {e}")
            raise

    async def find_candidate_files(self, search_patterns: List[str]) -> List[str]:
        search_tool = self.agent.get_tool_by_name("search_for_pattern")
        all_found_files = set()

        for pattern in search_patterns:
            logger.info(f"Serena: Scanning for import name '{pattern}'...")
            try:
                search_res = search_tool.apply(
                    substring_pattern=pattern,
                    restrict_search_to_code_files=True
                )
                parsed = self._parse_serena_output(search_res)
                if parsed:
                    all_found_files.update(parsed.keys())
            except Exception as e:
                logger.error(f"Serena search failed for {pattern}: {e}")

        return list(all_found_files)

    async def read_file(self, file_path: str) -> str:
        read_tool = self.agent.get_tool_by_name("read_file")
        try:
            return read_tool.apply(relative_path=file_path)
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return ""

    def _parse_serena_output(self, result) -> Any:
        raw = result.content if hasattr(result, 'content') else result
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(str(raw))
        except Exception as e:
            logger.error(f"Error when parsing {result}: {e}")
            return {}