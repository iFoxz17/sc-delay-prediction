class InvalidTMIParameters(Exception):
    """Exception raised for invalid TMI parameters."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"InvalidTMIParameters: {self.message}"