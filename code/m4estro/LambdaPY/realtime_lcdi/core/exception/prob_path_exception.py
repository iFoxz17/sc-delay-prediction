class ProbPathException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message: str = message

    def __str__(self) -> str:
        return self.message