
import logging

def setup_root_logger(file_name: str, *, console_level=logging.WARN, file_level=logging.DEBUG):

    logger = logging.getLogger()

    formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    file_handler = logging.FileHandler(file_name, encoding='utf-8')
    file_handler.setLevel(file_level)
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

