import logging
import json
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any
from serena.agent import SerenaAgent

logger = logging.getLogger(__name__)


class SerenaTool:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.agent = None

    async def start(self):
        """Ініціалізація та запуск Serena Agent."""
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

    async def find_usages_globally(self, library_name: str, api_whitelist: List[str]) -> List[Dict]:
        all_usages = []
        search_tool = self.agent.get_tool_by_name("search_for_pattern")
        read_tool = self.agent.get_tool_by_name("read_file")

        search_res = search_tool.apply(substring_pattern=library_name, restrict_search_to_code_files=True)
        candidate_files = self._parse_serena_output(search_res)

        if not candidate_files:
            return []

        for file_path in candidate_files.keys():
            try:
                content = read_tool.apply(relative_path=file_path)

                if not self._is_library_imported(content, library_name):
                    continue

                for method in api_whitelist:
                    if f".{method}" in content or f"{method}(" in content:
                        for line in content.splitlines():
                            if method in line and self._is_likely_code(line, method):
                                all_usages.append({
                                    "file": file_path,
                                    "pattern": line.strip(),
                                    "method_name": method
                                })
            except Exception as e:
                logger.error(f"File error {file_path}: {e}")

        return all_usages

    def _is_library_imported(self, content: str, lib: str) -> bool:
        patterns = [
            rf"import.*{lib}",  # Python, Java
            rf"require\(.*{lib}.*\)",  # JS/Node
            rf"from.*{lib}",  # TS/JS
            rf"using {lib}"  # C#
        ]
        return any(re.search(p, content, re.I) for p in patterns)

    def _is_likely_code(self, line: str, method: str) -> bool:
        line = line.strip()
        if line.startswith(("#", "//", "*", "import", "from")):
            return False
        return f".{method}" in line or f"{method}(" in line

    def _parse_serena_output(self, result) -> Any:
        raw = result.content if hasattr(result, 'content') else result
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(str(raw))
        except Exception as e:
            logger.error(f"Error when parsing {result}: {e}")
            return raw
