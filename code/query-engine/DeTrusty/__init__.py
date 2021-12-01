import logging


def get_logger(name, file=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if file is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(file)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
