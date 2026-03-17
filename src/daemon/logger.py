"""
Logging utility for ASURA Daemon
"""
import logging
from .config import LOG_FILE

def setup_logger(name='DAEMON', level=logging.INFO):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
    
    return logger

logger = setup_logger()
stone_logger = logger # Alias for consistency
