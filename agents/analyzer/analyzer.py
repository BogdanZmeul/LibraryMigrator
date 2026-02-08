import json
import os
import logging
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from agents.prompts.analyzer_prompts import ANALYZER_SYSTEM_TEMPLATE, FIX_SYSTEM_TEMPLATE
from agents.tools.io.json_handlers import load_json_file, save_json_file

logger = logging.getLogger(__name__)

BATCH_SIZE = 10
ANALYZER_MODEL = "claude-opus-4-6"


class MigrationExample(BaseModel):
    before: str
    after: str


class UsagePattern(BaseModel):
    pattern_id: int
    title: str
    status: str
    migration_guide: str
    occurrence_count: int
    affected_files: List[str]
    code_example: str
    migration_example: Optional[MigrationExample] = None


class MigrationTask(BaseModel):
    task_id: int
    title: str = Field(..., description="Short summary of the task")
    description: str = Field(..., description="Detailed technical instruction for the coder. MUST include the 'after' code example.")
    files: List[str]
    status: Literal["pending"] = "pending"


class MigrationBatch(BaseModel):
    tasks: List[MigrationTask]


def analyzer_node(state):
    logger.info("Analyzer: Starting process...")

    usage_path = state.get("usage_path", "usage.json")
    plan_path = state.get("plan_path", "migration_plan.json")
    errors_path = state.get("errors_path", "errors.json")

    user_message = state.get("message")
    additional_instructions = user_message if user_message else "No additional instructions provided."

    library = state.get("library")
    old_version = state.get("old_version")
    new_version = state.get("new_version")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    errors_data = load_json_file(errors_path)

    if errors_data:
        logger.info(f"Fixing mode activated. Found {len(errors_data)} errors.")
        mode = "fixing"
        input_data = errors_data
        system_template = FIX_SYSTEM_TEMPLATE
    else:
        logger.info("Planning mode activated.")
        mode = "planning"
        input_data = load_json_file(usage_path)
        system_template = ANALYZER_SYSTEM_TEMPLATE

    if not input_data:
        logger.warning("No input data found for processing. Exiting.")
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

    formatted_system_text = system_template.format(
        library=library,
        old_version=old_version,
        new_version=new_version,
        additional_instructions=additional_instructions
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

    existing_plan = []
    if mode == "fixing":
        existing_plan = load_json_file(plan_path)
        if not isinstance(existing_plan, list):
            existing_plan = []

    current_max_id = 0
    if existing_plan:
        current_max_id = max([t.get("task_id", 0) for t in existing_plan])

    total_items = len(input_data)
    new_tasks = []

    logger.info(f"Processing {total_items} items in batches of {BATCH_SIZE} with Prompt Caching")

    for i in range(0, total_items, BATCH_SIZE):
        batch = input_data[i: i + BATCH_SIZE]
        batch_json_str = json.dumps(batch, indent=2)
        batch_num = (i // BATCH_SIZE) + 1

        try:
            logger.debug(f"Sending batch {batch_num} to LLM...")

            if mode == "fixing":
                user_content = f"Fix these runtime errors:\n{batch_json_str}"
            else:
                user_content = f"Analyze this batch of usage patterns:\n{batch_json_str}"

            human_message = HumanMessage(content=user_content)

            result: MigrationBatch = structured_llm.invoke([system_message, human_message])

            for task in result.tasks:
                current_max_id += 1
                task.task_id = current_max_id
                new_tasks.append(task.model_dump())

            logger.info(f"Batch {batch_num} processed successfully. Generated {len(result.tasks)} tasks.")

        except Exception as e:
            logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
            continue

    if mode == "fixing":
        final_plan = existing_plan + new_tasks
        save_json_file(errors_path, [])
    else:
        final_plan = new_tasks

    save_json_file(plan_path, final_plan)

    return {
        "status": "plan_ready",
        "plan_path": plan_path
    }