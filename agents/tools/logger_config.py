import logging
import sys
import os

def setup_logger():
    """
    Налаштовує глобальний логер.
    Викликати цю функцію ТІЛЬКИ ОДИН РАЗ у main.py на самому початку.
    """
    log_filename = "agent.log"

    if not os.access("..", os.W_OK):
        if os.path.exists("/project"):
            log_filename = "/project/agent.log"
        else:
            log_filename = "/tmp/agent.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout) # косоль
        ],
        force=True
    )

    print(f"Логи записуються у файл: {log_filename}")

    return logging.getLogger(__name__)