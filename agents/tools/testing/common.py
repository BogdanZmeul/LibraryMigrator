import os
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RuntimeErrorData(BaseModel):
    error_id: int
    message: str
    context: str
    file: str


def get_code_context(file_path: str, line_number: int, context_window: int = 10) -> str:
    """
    Reads the file and returns lines around the specific line number.
    """
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found locally."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)
        # Lines are 1-indexed in traceback, but 0-indexed in list
        target_idx = line_number - 1

        start_idx = max(0, target_idx - context_window)
        end_idx = min(total_lines, target_idx + context_window + 1)

        snippet = []
        for i in range(start_idx, end_idx):
            prefix = ">> " if i == target_idx else "   "
            snippet.append(f"{prefix}{i + 1}: {lines[i].rstrip()}")

        return "\n".join(snippet)
    except Exception as e:
        logger.error(f"Failed to read context from {file_path}: {e}")
        return "Error reading code context."