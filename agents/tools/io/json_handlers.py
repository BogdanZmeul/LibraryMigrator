import json
import os
import logging
from typing import List, Dict, Union

logger = logging.getLogger(__name__)


def load_json_file(path: str) -> Union[List, Dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"JSON Load Error ({path}): {e}")
        return []


def save_json_file(path: str, data: Union[List, Dict]):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved data to {path}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")