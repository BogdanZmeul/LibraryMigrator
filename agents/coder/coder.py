import os
import logging
from typing import List, Dict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

# Imports from your project structure
from agents.tools.io.json_handlers import load_json_file, save_json_file
from agents.tools.io.file_ops import read_file, write_file
from agents.tools.git_ops import create_commit
from agents.prompts.coder_prompts import CODER_SYSTEM_TEMPLATE

logger = logging.getLogger(__name__)

CODER_MODEL = "claude-3-5-sonnet-latest"


def coder_node(state):
    logger.info("Coder: Waking up to check for pending tasks...")

    # --- 1. Load State & Config ---
    plan_path = state.get("plan_path", "migration_plan.json")
    project_path = state.get("project_path", ".")  # Default to current dir

    lib_name = state.get("lib_name", "library")
    from_ver = state.get("from_ver", "old")
    to_ver = state.get("to_ver", "new")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # --- 2. Load Plan ---
    migration_plan = load_json_file(plan_path)
    if not migration_plan:
        logger.warning("Migration plan is empty or invalid.")
        return {"status": "all_done"}

    # --- 3. Find Next Pending Task ---
    current_task = None
    task_index = -1

    for idx, task in enumerate(migration_plan):
        if task.get("status") == "pending":
            current_task = task
            task_index = idx
            break

    # If no pending tasks, we are finished
    if not current_task:
        logger.info("Coder: No pending tasks found. All done.")
        return {"status": "all_done"}

    logger.info(f"Coder: Picked up task {current_task['task_id']}: {current_task['title']}")

    # --- 4. Update Status to 'in_progress' ---
    migration_plan[task_index]["status"] = "in_progress"
    save_json_file(plan_path, migration_plan)

    # --- 5. Prepare Context (Read Files) ---
    # Here we read the actual content of the files to be edited.
    # Note: If we had Serena running, we could use semantic search here to narrow context,
    # but since we have explicit file paths from the Analyzer, reading them is safer for editing.
    files_to_edit = current_task.get("files", [])
    files_context = ""

    for file_path in files_to_edit:
        # Construct full path if needed, assuming file_path is relative to project root
        full_path = os.path.join(project_path, file_path)
        content = read_file(full_path)
        files_context += f"\n--- FILE: {file_path} ---\n{content}\n"

    # --- 6. Configure LLM with Tools ---
    # We explicitly bind the write_file tool so the LLM can use it
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
        return {"status": "error"}

    # --- 7. Build Prompt ---
    formatted_system = CODER_SYSTEM_TEMPLATE.format(
        lib_name=lib_name,
        from_ver=from_ver,
        to_ver=to_ver,
        task_title=current_task['title'],
        task_description=current_task['description'],
        file_list=", ".join(files_to_edit)
    )

    messages = [
        SystemMessage(content=formatted_system),
        HumanMessage(content=f"Here is the code context:\n{files_context}\n\nPlease perform the task.")
    ]

    # --- 8. Execute LLM (Editing Phase) ---
    try:
        logger.info("Coder: Invoking LLM to perform edits...")
        ai_msg = llm_with_tools.invoke(messages)

        # Check if tool calls exist (did the model try to write the file?)
        if ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                if tool_call["name"] == "write_file":
                    # Execute the tool
                    logger.info(f"Coder: Executing write_file for {tool_call['args']['file_path']}")
                    write_file(**tool_call["args"])
        else:
            logger.warning("Coder: LLM did not call write_file tool. Code might not be updated.")

    except Exception as e:
        logger.error(f"Coder: LLM execution failed: {e}")
        # Revert status to pending or mark as failed? For now, keep in_progress to debug
        return {"status": "error"}

    # --- 9. Commit Changes (Git) ---
    commit_msg = f"Refactor: {current_task['title']}"
    create_commit(project_path, commit_msg, description=current_task.get("description"))

    # --- 10. Update Status to 'done' ---
    # Reload plan in case it changed (unlikely in single thread but good practice)
    migration_plan = load_json_file(plan_path)

    # Update the specific task
    # We search by ID again to be safe
    for task in migration_plan:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = "done"
            break

    save_json_file(plan_path, migration_plan)
    logger.info(f"Coder: Task {current_task['task_id']} completed and saved.")

    # Return 'coding' to signal the graph to loop back to Coder
    # The Router will verify if there are pending tasks left
    return {
        "status": "coding",
        "plan_path": plan_path
    }