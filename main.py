import json
import asyncio
import typer
from dotenv import load_dotenv
from typing import Optional
from agents.logger_config import setup_logger
from agents.tools.git_ops import init_migration_branch
from agents.searcher.searcher import RepoSearcher

load_dotenv()
logger = setup_logger()

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
            searcher = RepoSearcher(project_path)

            usage_data = await searcher.execute_full_search(library, old_version, new_version)

            with open("usage.json", "w", encoding="utf-8") as f:
                json.dump(usage_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error during migration: {e}")
            raise typer.Exit(code=1)

    asyncio.run(run_async_migration())

if __name__ == "__main__":
    app()