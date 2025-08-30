from typing import List, Dict, Any, Optional
from core.sc_graph.utils import is_legal_index, IndexOutOfBoundsException, PathIndex, PathId, PathName

class PathMem:
    def __init__(self) -> None:
        self.paths: List[PathIndex] = []

    def to_json(self) -> List[PathIndex]:
        return self.paths
    
    @classmethod
    def from_json(cls, data: List[PathIndex]) -> 'PathMem':
        instance: PathMem = cls()
        instance.paths = data
        return instance


class VertexPathDPManager:
    def __init__(self, n: int) -> None:
        self.n: int = n
        self.mem: List[PathMem] = [PathMem() for _ in range(n)]

        self.updated: bool = False

    def _is_legal_index(self, v_index: int) -> bool:
        return is_legal_index(v_index, self.n)
            
    def add(self, v_index: int, path: PathIndex) -> None:
        if not self._is_legal_index(v_index):
            raise IndexOutOfBoundsException(v_index, self.n)
        
        self.mem[v_index].paths.append(path)

        self.updated = True

    def contains(self, v_index: int) -> bool:
        if not self._is_legal_index(v_index):
            raise IndexOutOfBoundsException(v_index, self.n)
        
        return len(self.mem[v_index].paths) > 0

    def get(self, v_index: int) -> List[PathIndex]:
        if not self._is_legal_index(v_index):
            raise IndexOutOfBoundsException(v_index, self.n)
        
        return self.mem[v_index].paths
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "mem": [mem.to_json() for mem in self.mem]
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'VertexPathDPManager':
        n: int = data.get("n", 0)
        mem_data: List[List[PathIndex]] = data.get("mem", [])
        
        instance: VertexPathDPManager = cls(n)
        instance.mem = [PathMem.from_json(paths) for paths in mem_data]
        return instance
    
    
class PathDPManager():
    def __init__(self, n: int) -> None:
        self.n: int = n
        self.v_path_dp_managers: List[VertexPathDPManager] = [VertexPathDPManager(n) for _ in range(n)]

    def get(self, v_index: int) -> VertexPathDPManager:
        if not is_legal_index(v_index, self.n):
            raise IndexOutOfBoundsException(v_index, self.n)
        
        return self.v_path_dp_managers[v_index]

    def is_updated(self) -> bool:
        return any(p_dp_manager.updated for p_dp_manager in self.v_path_dp_managers)

    def to_json(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "v_paths_dp_managers": [v_dp_manager.to_json() for v_dp_manager in self.v_path_dp_managers]
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'PathDPManager':
        n: int = data.get("n", 0)
        v_path_dp_managers_data: List[Dict[str, Any]] = data.get("v_paths_dp_managers", [])

        instance: PathDPManager = cls(n)
        instance.v_path_dp_managers = [VertexPathDPManager.from_json(v_dp_manager_data) for v_dp_manager_data in v_path_dp_managers_data]
        return instance

