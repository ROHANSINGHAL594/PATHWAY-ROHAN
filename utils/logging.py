from typing import Optional
import logging

def configure_root(level: int = logging.INFO):
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        formatter = logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level)

def get_logger(name: Optional[str] = None, level: int = logging.INFO):
    configure_root(level)
    return logging.getLogger(name)


