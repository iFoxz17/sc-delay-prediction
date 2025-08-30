from abc import ABC

class VertexNotFoundException(Exception, ABC):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class VertexIdNotFoundException(VertexNotFoundException):
    def __init__(self, vertex_id: int) -> None:
        super().__init__(f"Vertex with ID {vertex_id} not found.")
        self.vertex_id: int = vertex_id

    def __str__(self) -> str:
        return f"Vertex with ID {self.vertex_id} not found."
    

class VertexNameNotFoundException(VertexNotFoundException):
    def __init__(self, vertex_name: str) -> None:
        super().__init__(f"Vertex with name '{vertex_name}' not found.")
        self.vertex_name: str = vertex_name

    def __str__(self) -> str:
        return f"Vertex with name '{self.vertex_name}' not found."

class VertexNameTypeNotFoundException(VertexNameNotFoundException):
    def __init__(self, vertex_name: str, vertex_type: str) -> None:
        super().__init__(vertex_name)
        self.vertex_type: str = vertex_type

    def __str__(self):
        return f"Vertex with name '{self.vertex_name}' and type '{self.vertex_type}' not found."
    
