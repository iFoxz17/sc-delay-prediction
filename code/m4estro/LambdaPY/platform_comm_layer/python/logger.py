from aws_lambda_powertools import Logger

def get_logger(name: str = None) -> Logger:
    return Logger(service = name or __name__)