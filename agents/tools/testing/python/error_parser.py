import re
import os
import logging
from typing import List, Dict
from agents.tools.testing.common import RuntimeErrorData, get_code_context

logger = logging.getLogger(__name__)


def parse_python_traceback(stderr: str, project_path: str) -> List[Dict]:
    """
    Parses Python stderr to extract structured errors.
    """
    errors = []
    error_id_counter = 0

    file_pattern = re.compile(r'File "(?P<path>.*?)", line (?P<line>\d+), in (?P<func>.*)')

    error_msg_pattern = re.compile(r'^(?P<type>\w+Error|Exception): (?P<msg>.*)$', re.MULTILINE)

    traceback_blocks = stderr.split("Traceback (most recent call last):")

    # Skip the first empty block (text before the first traceback)
    for block in traceback_blocks[1:]:
        error_id_counter += 1

        # 1. Find the error message (usually at the end)
        error_match = error_msg_pattern.search(block)
        error_message = "Unknown Runtime Error"
        if error_match:
            error_message = f"{error_match.group('type')}: {error_match.group('msg')}"

        # 2. Find the relevant file causing the error
        # We iterate through all matches and pick the last one that is NOT in site-packages
        # because we want to fix user code, not library internals.
        matches = list(file_pattern.finditer(block))
        relevant_match = None

        for m in reversed(matches):
            path = m.group("path")
            # Basic filter to ignore system libs
            if "site-packages" not in path and "dist-packages" not in path and "<frozen" not in path:
                relevant_match = m
                break

        # If no user code found, fallback to the very last frame
        if not relevant_match and matches:
            relevant_match = matches[-1]

        if relevant_match:
            file_path_raw = relevant_match.group("path")
            line_no = int(relevant_match.group("line"))

            # Normalize path (remove Docker /app/ prefix if present)
            # Assuming project_path is the root.
            # If path is absolute, try to make it relative to project root
            rel_path = file_path_raw
            if os.path.isabs(file_path_raw):
                # Simple heuristic: try to find the filename in the project tree
                # For now, just taking the basename if absolute path doesn't match local structure
                if not os.path.exists(file_path_raw):
                    rel_path = os.path.basename(file_path_raw)

            # Try to resolve full local path for context reading
            local_full_path = os.path.join(project_path, rel_path)
            if not os.path.exists(local_full_path):
                # Search recursively if path mapping failed (fallback)
                for root, _, files in os.walk(project_path):
                    if rel_path in files:
                        local_full_path = os.path.join(root, rel_path)
                        rel_path = os.path.relpath(local_full_path, project_path)
                        break

            # 3. Get Context
            context_code = get_code_context(local_full_path, line_no)

            error_obj = RuntimeErrorData(
                error_id=error_id_counter,
                message=error_message,
                context=context_code,
                file=rel_path
            )
            errors.append(error_obj.model_dump())

    return errors