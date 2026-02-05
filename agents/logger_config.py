import logging
import sys

def setup_logger():
    """
    Налаштовує глобальний логер.
    Викликати цю функцію ТІЛЬКИ ОДИН РАЗ у main.py на самому початку.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("agent.log", mode='w', encoding='utf-8'),
            # logging.StreamHandler(sys.stdout) # косоль
        ],
        force=True
    )
    return logging.getLogger(__name__)