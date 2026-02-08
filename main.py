import asyncio
import typer
from dotenv import load_dotenv
from typing import Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from agents.tools.logger_config import setup_logger
from agents.tools.git_ops import init_migration_branch, cleanup_migration_artifacts
from agents.searcher.searcher import searcher_node
from agents.analyzer.analyzer import analyzer_node
from agents.coder.coder import coder_node
from agents.tester.tester import tester_node

load_dotenv()
logger = setup_logger()

class MigrationState(TypedDict, total=False):
    project_path: str
    library: str
    old_version: str
    new_version: str
    message: Optional[str]
    usage_path: str
    plan_path: str
    errors_path: str
    status: str
    has_pending_tasks: bool
    needs_analysis: bool


def route_after_coder(state: MigrationState) -> str:
    if state.get("has_pending_tasks"):
        logger.info("Router: Pending tasks remain. Returning to coder.")
        return "coder"
    logger.info("Router: No pending tasks remain. Moving to tester.")
    return "tester"


def route_after_tester(state: MigrationState) -> str:
    if state.get("needs_analysis"):
        logger.info("Router: Test errors detected. Returning to analyzer.")
        return "analyzer"
    logger.info("Router: Tests complete. Finishing.")
    return "end"


def build_graph():
    builder = StateGraph(MigrationState)
    builder.add_node("searcher", searcher_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("coder", coder_node)
    builder.add_node("tester", tester_node)

    builder.add_edge(START, "searcher")
    builder.add_edge("searcher", "analyzer")
    builder.add_edge("analyzer", "coder")
    builder.add_conditional_edges(
        "coder",
        route_after_coder,
        {"coder": "coder", "tester": "tester"}
    )
    builder.add_conditional_edges(
        "tester",
        route_after_tester,
        {"analyzer": "analyzer", "end": END}
    )
    return builder.compile()


GRAPH = build_graph()

app = typer.Typer(help="AI Migrator — tool for automatic library updates.")

@app.command()
def migrate(
    project_path: str = typer.Argument("/project", help="Path to the project inside the container"),
    library: str = typer.Option(..., "--lib", "-l", help="Library name"),
    old_version: str = typer.Option(..., "--from", "-ov", help="Current version"),
    new_version: str = typer.Option(..., "--to", "-nv", help="Target version"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Additional instructions for AI")
):
    logger.info(f"Library migration: {library} ({old_version} -> {new_version})")
    if message:
        logger.info(f"Additional prompt: {message}")

    async def run_async_migration():
        try:
            init_migration_branch(project_path)
            initial_state: MigrationState = {
                "project_path": project_path,
                "library": library,
                "old_version": old_version,
                "new_version": new_version,
                "message": message,
                "usage_path": "usage.json",
                "plan_path": "migration_plan.json",
                "errors_path": "errors.json"
            }

            final_state = await GRAPH.ainvoke(initial_state)
            cleanup_migration_artifacts(project_path)
            logger.info(f"Migration finished with status: {final_state.get('status')}")

        except Exception as e:
            logger.error(f"Error during migration: {e}")
            raise typer.Exit(code=1)

    asyncio.run(run_async_migration())

if __name__ == "__main__":
    app()
