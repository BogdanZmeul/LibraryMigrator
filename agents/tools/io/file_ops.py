import os
import logging

logger = logging.getLogger(__name__)


def read_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return f"Error: File {file_path} does not exist."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Read file: {file_path}")
        return content
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return f"Error reading file: {e}"


def write_file(file_path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Successfully wrote to file: {file_path}")
        return f"Successfully updated {file_path}"
    except Exception as e:
        logger.error(f"Failed to write to {file_path}: {e}")
        return f"Error writing file: {e}"