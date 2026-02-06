import subprocess
import os
import logging

logger = logging.getLogger(__name__)


def init_migration_branch(path: str):
    """
    Готує існуючий репозиторій: налаштовує Git та створює нову гілку.
    """
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", path], check=True)

    if not os.path.exists(path) or not os.listdir(path):
        raise Exception(f"Папка {path} порожня або не існує. Перевірте монтаж Volume.")

    files = os.listdir(path)

    if '.git' not in files:
        raise Exception(
            f"У папці {path} не знайдено прихованої директорії .git. Ви впевнені, що це корінь репозиторію?")

    try:
        subprocess.run(["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
                       check=True, capture_output=True)

        status = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                                capture_output=True, text=True, check=True)

        if status.stdout.strip():
            logger.info("Знайдено незакомічені зміни. Виконую 'git stash'...")
            subprocess.run(["git", "-C", path, "stash"], check=True)
            logger.info("'git stash' успішно виконано!")

        subprocess.run(["git", "-C", path, "config", "user.email", "agent@ai.com"], check=True)
        subprocess.run(["git", "-C", path, "config", "user.name", "AI Migrator Agent"], check=True)

        branch_name = "fix/ai-library-migration"
        subprocess.run(["git", "-C", path, "checkout", "-B", branch_name], check=True)

        logger.info(f"Перемкнуто на гілку: {branch_name}")

    except subprocess.CalledProcessError:
        logger.error(f"Помилка: Папка {path} не містить Git-репозиторію.")
        raise


def create_commit(path: str, title: str, description: str = None):
    """
    Робить коміт змін у робочій папці.
    """
    try:
        status = subprocess.run(["git", "-C", path, "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            logger.warning("Немає змін для коміту.")
            return

        subprocess.run(["git", "-C", path, "add", "."], check=True)

        cmd = ["git", "-C", path, "commit", "-m", title]
        if description:
            cmd += ["-m", description]

        subprocess.run(cmd, check=True)
        logger.info(f"Створено коміт: {title}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Не вдалося створити коміт: {e}")