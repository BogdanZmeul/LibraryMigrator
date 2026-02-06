import json
import os
import logging
from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from agents.prompts.analyzer_prompts import ANALYZER_SYSTEM_TEMPLATE

logger = logging.getLogger(__name__)

BATCH_SIZE = 10
ANALYZER_MODEL = "claude-3-5-sonnet-latest"


class UsagePattern(BaseModel):
    pattern_id: int
    title: str
    code_example: str
    migration_guide: str
    files: List[str]


class MigrationTask(BaseModel):
    task_id: int
    title: str = Field(..., description="Short summary of the task")
    description: str = Field(..., description="Detailed technical instruction for the coder")
    files: List[str]
    status: Literal["pending"] = "pending"


class MigrationBatch(BaseModel):
    tasks: List[MigrationTask]


def analyzer_node(state):
    logger.info("Analyzer: Starting migration plan generation...")

    usage_path = state.get("usage_path", "usage.json")
    plan_path = state.get("plan_path", "migration_plan.json")

    lib_name = state.get("lib_name")
    from_ver = state.get("from_ver")
    to_ver = state.get("to_ver")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not os.path.exists(usage_path):
        logger.error(f"Input file not found: {usage_path}")
        return {"status": "error", "error": "Usage file missing"}

    try:
        with open(usage_path, "r", encoding="utf-8") as f:
            usage_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from {usage_path}: {e}")
        return {"status": "error", "error": "Invalid usage JSON"}

    if not usage_data:
        logger.warning(f"Usage data is empty in {usage_path}. Nothing to plan.")
        return {"status": "done", "plan_path": plan_path}

    try:
        llm = ChatAnthropic(
            model_name=ANALYZER_MODEL,
            temperature=0,
            api_key=api_key
        )
        structured_llm = llm.with_structured_output(MigrationBatch)
    except Exception as e:
        logger.critical(f"Failed to initialize LLM: {e}")
        return {"status": "error", "error": "LLM init failed"}

    formatted_system_text = ANALYZER_SYSTEM_TEMPLATE.format(
        lib_name=lib_name,
        from_ver=from_ver,
        to_ver=to_ver
    )

    system_message = SystemMessage(
        content=[
            {
                "type": "text",
                "text": formatted_system_text,
                "cache_control": {"type": "ephemeral"}
            }
        ]
    )

    total_patterns = len(usage_data)
    all_tasks = []
    current_task_id = 0

    logger.info(f"Processing {total_patterns} patterns in batches of {BATCH_SIZE} with Prompt Caching")

    for i in range(0, total_patterns, BATCH_SIZE):
        batch = usage_data[i: i + BATCH_SIZE]
        batch_json_str = json.dumps(batch, indent=2)
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total_patterns + BATCH_SIZE - 1)

        try:
            logger.debug(f"Sending batch {batch_num}/{total_batches} to LLM...")
            human_message = HumanMessage(
                content=f"Analyze this batch of usage patterns:\n{batch_json_str}"
            )

            result: MigrationBatch = structured_llm.invoke([system_message, human_message])

            for task in result.tasks:
                current_task_id += 1
                task.task_id = current_task_id
                all_tasks.append(task.model_dump())

            logger.info(f"Batch {batch_num}/{total_batches} processed successfully. Generated {len(result.tasks)} tasks.")

        except Exception as e:
            logger.error(f"Error processing batch {batch_num} (indices {i}-{i + BATCH_SIZE}): {e}", exc_info=True)
            continue

    try:
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(all_tasks, f, indent=2, ensure_ascii=False)
        logger.info(f"Migration plan successfully saved to {plan_path} ({len(all_tasks)} tasks total).")
    except IOError as e:
        logger.error(f"Failed to write migration plan to disk: {e}")
        return {"status": "error", "error": "Write failed"}

    return {
        "status": "plan_ready",
        "plan_path": plan_path
    }