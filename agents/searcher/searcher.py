import logging
from ..tools.serena_tool import SerenaTool
from ..tools.context7_tool import Context7Tool
from .context7_refiner import Context7Refiner

logger = logging.getLogger(__name__)


class RepoSearcher:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.serena = SerenaTool(project_path)
        self.context_ai = Context7Tool()
        self.context_refiner = Context7Refiner()

    async def execute_full_search(self, library: str, old_v: str, new_v: str):
        logger.info(f"Universal search: {library} ({old_v} -> {new_v})")

        await self.serena.start()

        logger.info("Getting the official API list...")
        raw_api = await self.context_ai.get_library_public_api(library, old_v)

        if not raw_api:
            logger.error("Failed to get API list. Aborting.")
            return []

        api_whitelist = await self.context_refiner.refine_api_list(raw_api)

        valid_api_names = set(api_whitelist)
        logger.info(f"Retrieved {len(valid_api_names)} valid methods from the documentation.")

        raw_usages = await self.serena.find_usages_globally(library, api_whitelist)

        grouped_methods = {}
        for item in raw_usages:
            name = item.get('method_name', '')

            if name not in valid_api_names:
                continue

            if name not in grouped_methods:
                grouped_methods[name] = []
            grouped_methods[name].append(item)

        report = []
        method_names = list(grouped_methods.keys())

        for i, method in enumerate(method_names):
            items = grouped_methods[method]
            full_query = f"{library}.{method}"

            logger.info(f"[{i + 1}/{len(method_names)}] Migration analysis for {full_query}...")

            raw_advice = await self.context_ai.get_migration_advice(library, full_query, old_v, new_v)

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