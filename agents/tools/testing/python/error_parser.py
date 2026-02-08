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

    for block in traceback_blocks[1:]:
        error_id_counter += 1

        error_match = error_msg_pattern.search(block)
        error_message = "Unknown Runtime Error"
        if error_match:
            error_message = f"{error_match.group('type')}: {error_match.group('msg')}"

        matches = list(file_pattern.finditer(block))
        relevant_match = None

        for m in reversed(matches):
            path = m.group("path")
            if "site-packages" not in path and "dist-packages" not in path and "<frozen" not in path:
                relevant_match = m
                break

        if not relevant_match and matches:
            relevant_match = matches[-1]

        if relevant_match:
            file_path_raw = relevant_match.group("path")
            line_no = int(relevant_match.group("line"))

            rel_path = file_path_raw
            if os.path.isabs(file_path_raw):
                if not os.path.exists(file_path_raw):
                    rel_path = os.path.basename(file_path_raw)

            local_full_path = os.path.join(project_path, rel_path)
            if not os.path.exists(local_full_path):
                for root, _, files in os.walk(project_path):
                    if rel_path in files:
                        local_full_path = os.path.join(root, rel_path)
                        rel_path = os.path.relpath(local_full_path, project_path)
                        break

            context_code = get_code_context(local_full_path, line_no)

            error_obj = RuntimeErrorData(
                error_id=error_id_counter,
                message=error_message,
                context=context_code,
                file=rel_path
            )
            errors.append(error_obj.model_dump())

    return errors