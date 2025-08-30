class VertexNotFoundException(Exception):
    def __init__(self, message: str = "Vertex not found"):
        super().__init__(message)
        self.message = message