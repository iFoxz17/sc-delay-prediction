from typing import override, Optional, Tuple, List, Any
import json
import igraph as ig

from serializer.graph_serializer import GraphSerializer

GRAPH_PATH = '.\\'
GRAPH_FILENAME = 'sc_graph.json'

class FileGraphSerializer(GraphSerializer):
    def __init__(self):
        super().__init__()

    def _get_file_path(self, maybe_path: Optional[str], maybe_filename: Optional[str]) -> str:
        filename: str = maybe_filename or GRAPH_FILENAME
        path: str = maybe_path or GRAPH_PATH
        if not path.endswith('\\'):
            return path  
        
        return f"{path}\\{filename}"

    @override
    def serialize(self, graph: ig.Graph, path: Optional[str] = None, filename: Optional[str] = None) -> None:
        filepath: str = self._get_file_path(path, filename)
        try:
            g_data: Tuple[List[Any], List[Any]] = self.to_json(graph)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(g_data, f, indent=2)
        except Exception as e:
            raise e       

    @override
    def deserialize(self, path: Optional[str] = None, filename: Optional[str] = None) -> ig.Graph:
        file_path: str = self._get_file_path(path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data: Any = json.load(f)
            return self.from_json(data)
        except Exception as e:
            raise e