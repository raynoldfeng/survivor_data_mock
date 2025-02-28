# log.py
import logging

class Log:
    _instance = None

    def __new__(cls, level=logging.INFO, filename=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logger = logging.getLogger(__name__)
            cls._instance.logger.setLevel(level)

            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            if filename:
                # 输出到文件
                file_handler = logging.FileHandler(filename)
                file_handler.setFormatter(formatter)
                cls._instance.logger.addHandler(file_handler)

            # 输出到控制台
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            cls._instance.logger.addHandler(console_handler)
        return cls._instance

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warn(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)