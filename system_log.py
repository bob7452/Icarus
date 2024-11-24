import os
import logging

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "system_log.log")

log_dir = os.path.dirname(LOG_FILE)
if LOG_FILE and not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,  # 設置最低級別: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),  # 輸出到檔案
        logging.StreamHandler()  # 輸出到終端
    ]
)

logger = logging.getLogger(__name__)

def debug(message):
    logger.debug(message)

def info(message):
    logger.info(message)

def warning(message):
    logger.warning(message)

def error(message):
    logger.error(message)

def critical(message):
    logger.critical(message)