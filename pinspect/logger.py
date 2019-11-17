import logging
import time
from pathlib import Path


def init_logger():
    logpath = Path(f"logs/{time.strftime('%Y.%m.%d %H:%M')}.txt")
    logpath.parent.mkdir(exist_ok=True)
    logging.basicConfig(filename=logpath, level=logging.DEBUG)
