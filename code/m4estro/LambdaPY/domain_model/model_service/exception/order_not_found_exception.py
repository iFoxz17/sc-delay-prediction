class OrderNotFoundException(Exception):
    def __init__(self, message: str = "Order not found"):
        super().__init__(message)
        self.message = message