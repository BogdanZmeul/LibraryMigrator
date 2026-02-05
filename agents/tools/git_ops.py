import subprocess
import os
import logging
import shutil

logger = logging.getLogger(__name__)

SANDBOX_DIR = "/app/sandbox"


def clean_sandbox():
    if not os.path.exists(SANDBOX_DIR):
        os.makedirs(SANDBOX_DIR, exist_ok=True)
        return

    logger.info("Очищення папки sandbox...")

    for filename in os.listdir(SANDBOX_DIR):
        file_path = os.path.join(SANDBOX_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f"Не вдалося видалити {file_path}. Причина: {e}")
            raise


def prepare_repo(source: str):
    logging.info(f"Початок підготовки репозиторію з: {source}")

    clean_sandbox()

    try:
        logger.info(f"Клонування репозиторію в {SANDBOX_DIR}...")
        subprocess.run(["git", "clone", source, SANDBOX_DIR], check=True)

        subprocess.run(["git", "-C", SANDBOX_DIR, "config", "user.email", "agent@ai.com"], check=True)
        subprocess.run(["git", "-C", SANDBOX_DIR, "config", "user.name", "AI Agent"], check=True)

        subprocess.run(["git", "-C", SANDBOX_DIR, "checkout", "-b", "ai-fix"], check=True)
        logger.info("Гілка 'ai-fix' створена успішно.")

    except subprocess.CalledProcessError as e:
        logger.error(f"🔥 Помилка Git: {e}")
        raise e


def create_commit(title: str, description: str = None):
    try:
        status = subprocess.run(["git", "-C", SANDBOX_DIR, "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            logger.warning("⚠️ Немає змін для коміту.")
            return

        subprocess.run(["git", "-C", SANDBOX_DIR, "add", "."], check=True)

        cmd = ["git", "-C", SANDBOX_DIR, "commit", "-m", title]
        if description:
            cmd += ["-m", description]

        subprocess.run(cmd, check=True)
        logger.info(f"Створено коміт: {title}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Не вдалося створити коміт: {e}")