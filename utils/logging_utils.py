import logging
import os
from logging.handlers import RotatingFileHandler

def set_system_logger(name: str, level: int = logging.INFO, log_file: str = None) -> logging.Logger:
    """
    Sets up and returns a system logger with the specified name and logging level.
    Optionally logs to a file with rotation.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Common formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 1. Create console handler
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # 2. Optionally create file handler
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == os.path.abspath(log_file) for h in logger.handlers):
            fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
            fh.setLevel(level)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    return logger