import subprocess
import os
import logging
import shutil

logger = logging.getLogger(__name__)


def init_migration_branch(path: str):
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", path], check=True)

    if not os.path.exists(path) or not os.listdir(path):
        raise Exception(f"The folder {path} is empty or does not exist. Check the Volume mount.")

    files = os.listdir(path)

    if '.git' not in files:
        raise Exception(
            f"No hidden .git directory found in folder {path}. Are you sure this is the root of the repository?")

    try:
        subprocess.run(["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
                       check=True, capture_output=True)

        status = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                                capture_output=True, text=True, check=True)

        if status.stdout.strip():
            logger.info("Found uncommitted changes. Running 'git stash'...")
            subprocess.run(["git", "-C", path, "stash"], check=True)
            logger.info("'git stash' successfully executed!")

        subprocess.run(["git", "-C", path, "config", "user.email", "agent@ai.com"], check=True)
        subprocess.run(["git", "-C", path, "config", "user.name", "AI Migrator Agent"], check=True)

        branch_name = "fix/ai-library-migration"
        subprocess.run(["git", "-C", path, "checkout", "-B", branch_name], check=True)

        logger.info(f"Switched to branch: {branch_name}")

    except subprocess.CalledProcessError:
        logger.error(f"Error: The folder {path} does not contain a Git repository.")
        raise


def create_commit(path: str, title: str, description: str = None):
    try:
        status = subprocess.run(
            ["git", "-C", path, "status", "--porcelain", "--", ".", ":!.serena"],
            capture_output=True, text=True, check=True
        )

        if not status.stdout.strip():
            logger.warning("There are no changes to the commit.")
            return

        subprocess.run(["git", "-C", path, "add", ".", ":!.serena"], check=True)

        cmd = ["git", "-C", path, "commit", "-m", title]
        if description:
            cmd += ["-m", description]

        subprocess.run(cmd, check=True)
        logger.info(f"Commit created: {title}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create commit: {e}")

def cleanup_migration_artifacts(path: str):
    serena_path = os.path.join(path, ".serena")
    if os.path.exists(serena_path):
        try:
            shutil.rmtree(serena_path)
            logger.info(f"Successfully cleaned up {serena_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup .serena folder: {e}")