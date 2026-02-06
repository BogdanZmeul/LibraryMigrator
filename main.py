import typer
from typing import Optional
from agents.logger_config import setup_logger
from agents.tools.git_ops import init_migration_branch

logger = setup_logger()

app = typer.Typer(help="AI Migrator — інструмент для автоматичного оновлення бібліотек.")

@app.command()
def migrate(
    project_path: str = typer.Argument("/project", help="Шлях до проєкту всередині контейнера"),
    library: str = typer.Option(..., "--lib", "-l", help="Назва бібліотеки"),
    old_version: str = typer.Option(..., "--from", "-ov", help="Поточна версія"),
    new_version: str = typer.Option(..., "--to", "-nv", help="Цільова версія"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Додаткові інструкції для AI")
):
    """
    Запускає міграцію конкретної бібліотеки.
    """
    logger.info(f"Міграція бібліотеки: {library} ({old_version} -> {new_version})")
    if message:
        logger.info(f"Додатковий промпт: {message}")

    try:
        init_migration_branch(project_path)
        logger.info("Завдання виконано!")
    except Exception as e:
        logger.error(f"Помилка: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()