import os
import logging
from typing import List, Dict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from agents.tools.io.json_handlers import load_json_file, save_json_file
from agents.tools.io.file_ops import read_file, write_file
from agents.tools.git_ops import create_commit
from agents.prompts.coder_prompts import CODER_SYSTEM_TEMPLATE

logger = logging.getLogger(__name__)

CODER_MODEL = "claude-opus-4-6"


def coder_node(state):
    logger.info("Coder: Start working...")

    user_message = state.get("message")
    additional_instructions = user_message if user_message else "No additional instructions provided."

    plan_path = state.get("plan_path", "migration_plan.json")
    project_path = state.get("project_path", ".")

    library = state.get("library", "library")
    old_version = state.get("old_version", "old")
    new_version = state.get("new_version", "new")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    migration_plan = load_json_file(plan_path)
    if not migration_plan:
        logger.warning("Migration plan is empty or invalid.")
        return {
            "status": "all_done",
            "plan_path": plan_path,
            "has_pending_tasks": False
        }

    current_task = None
    task_index = -1

    for idx, task in enumerate(migration_plan):
        if task.get("status") == "pending":
            current_task = task
            task_index = idx
            break

    if not current_task:
        logger.info("Coder: No pending tasks found. All done.")
        return {
            "status": "all_done",
            "plan_path": plan_path,
            "has_pending_tasks": False
        }

    logger.info(f"Coder: Picked up task {current_task['task_id']}: {current_task['title']}")

    migration_plan[task_index]["status"] = "in_progress"
    save_json_file(plan_path, migration_plan)

    files_to_edit = current_task.get("files", [])
    files_context = ""

    for file_path in files_to_edit:
        full_read_path = os.path.join(project_path, file_path)
        content = read_file(full_read_path)
        files_context += f"\n--- FILE: {file_path} ---\n{content}\n"

    tools = [write_file]

    try:
        llm = ChatAnthropic(
            model_name=CODER_MODEL,
            temperature=0,
            api_key=api_key
        )
        llm_with_tools = llm.bind_tools(tools)
    except Exception as e:
        logger.critical(f"Failed to initialize Coder LLM: {e}")
        return {
            "status": "error",
            "plan_path": plan_path,
            "has_pending_tasks": False
        }

    formatted_system = CODER_SYSTEM_TEMPLATE.format(
        library=library,
        old_version=old_version,
        new_version=new_version,
        task_title=current_task['title'],
        task_description=current_task['description'],
        file_list=", ".join(files_to_edit),
        additional_instructions=additional_instructions
    )

    messages = [
        SystemMessage(content=formatted_system),
        HumanMessage(content=f"Here is the code context:\n{files_context}\n\nPlease perform the task.")
    ]

    changes_made = False
    try:
        logger.info("Coder: Invoking LLM to perform edits...")
        ai_msg = llm_with_tools.invoke(messages)

        if ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                if tool_call["name"] == "write_file":
                    args = tool_call["args"]
                    args["file_path"] = os.path.join(project_path, args["file_path"])
                    logger.info(f"Coder: Executing write_file for {tool_call['args']['file_path']}")
                    write_file(**tool_call["args"])
                    changes_made = True
        else:
            logger.info("Coder: LLM decided no changes are needed for these files.")

    except Exception as e:
        logger.error(f"Coder: LLM execution failed: {e}")
        return {
            "status": "error",
            "plan_path": plan_path,
            "has_pending_tasks": False
        }

    if changes_made:
        commit_msg = f"Refactor: {current_task['title']}"
        create_commit(project_path, commit_msg, description=current_task.get("description"))
    else:
        logger.info(f"Coder: Skipping commit for task {current_task['task_id']} (no changes made).")

    migration_plan = load_json_file(plan_path)

    for task in migration_plan:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = "done"
            break

    save_json_file(plan_path, migration_plan)
    logger.info(f"Coder: Task {current_task['task_id']} completed and saved.")

    has_pending_tasks = any(task.get("status") == "pending" for task in migration_plan)
    if has_pending_tasks:
        logger.info("Coder: Pending tasks remain after this run.")
    else:
        logger.info("Coder: No pending tasks remain after this run.")

    return {
        "status": "coding" if has_pending_tasks else "all_done",
        "plan_path": plan_path,
        "has_pending_tasks": has_pending_tasks
    }
