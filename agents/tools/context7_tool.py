import httpx
import os
import logging
from typing import Dict, Any, Optional
from agents.prompts.searcher_prompts import MIGRATION_ADVICE_PROMPT

logger = logging.getLogger(__name__)


class Context7Tool:
    def __init__(self):
        self.base_url = "https://context7.com/api/v2"
        self.api_key = os.environ.get("CONTEXT7_API_KEY")
        self.library_ids = {}

    async def get_migration_advice(self, library: str, element: str, old_v: str, new_v: str) -> str:
        real_id = await self._resolve_library_id(library)
        if not real_id:
            return "Library not found."

        query = MIGRATION_ADVICE_PROMPT.format(
            library=library, element=element, old_v=old_v, new_v=new_v
        )
        data = await self._make_txt_request(real_id, query)

        return data

    async def _make_txt_request(self, library_id: str, query: str) -> Dict[str, Any]:
        if not self.api_key:
            return {}

        params = {
            "libraryId": library_id,
            "query": query,
            "type": "txt"
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.get(f"{self.base_url}/context", params=params, headers=headers)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"Error Context7: {e}")
                return {}

    async def _resolve_library_id(self, library_name: str) -> Optional[str]:
        if library_name in self.library_ids:
            return self.library_ids[library_name]

        logger.info(f"Search for technical ID for '{library_name}'...")

        params = {
            "libraryName": library_name,
            "query": "stable documentation"
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/libs/search", params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                if results:
                    found_id = results[0]["id"]
                    self.library_ids[library_name] = found_id
                    logger.info(f"Founded ID: {found_id}")
                    return found_id

            except Exception as e:
                logger.error(f"Library ID lookup error: {e}")

        return None