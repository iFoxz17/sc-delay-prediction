from typing import Dict, List, Optional, Any

from core.sc_graph.utils import IndexOutOfBoundsException, CarrierNotFoundException, is_legal_index

class ProbMem:
    def __init__(self) -> None:
        self.probs: List[float] = []

    def to_json(self) -> List[float]:
        return self.probs
    
    @classmethod
    def from_json(cls, data: List[float]) -> 'ProbMem':
        instance: ProbMem = cls()
        instance.probs = data
        return instance

class PathProbDPManager:
    def __init__(self, n: int) -> None:
        self.n: int = n
        self.mem: Dict[str, List[ProbMem]] = {}

        self.updated: bool = False
                
    def add(self, carrier: str, v_index: int, prob: float) -> None:
        n: int = self.n
        if not is_legal_index(v_index, n):
            raise IndexOutOfBoundsException(v_index, n)
        
        if not carrier in self.mem:
            self.mem[carrier] = [ProbMem() for _ in range(n)]
    
        self.mem[carrier][v_index].probs.append(prob)

        self.updated = True

    def contains(self, carrier: str, maybe_v_index: Optional[int] = None) -> bool:
        if not carrier in self.mem:
            return False
            
        if not maybe_v_index:
            return True

        if not is_legal_index(maybe_v_index, self.n):
            raise IndexOutOfBoundsException(maybe_v_index, self.n)
                
        return len(self.mem[carrier][maybe_v_index].probs) > 0
    
    def get(self, carrier: str, v_index: int) -> List[float]:
        if carrier not in self.mem:
            raise CarrierNotFoundException(carrier)
        
        if not is_legal_index(v_index, self.n):
            raise IndexOutOfBoundsException(v_index, self.n)
        
        return self.mem[carrier][v_index].probs
    
    def is_updated(self) -> bool:
        return self.updated
       
    def to_json(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "mem": {
                carrier: [mem.to_json() for mem in mems]
                for carrier, mems in self.mem.items()
            }
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'PathProbDPManager':
        n: int = data.get("n", 0)
        mem_data: Dict[str, List[List[float]]] = data.get("mem", {})
        
        instance: PathProbDPManager = cls(n)
        instance.mem = {
            carrier: [ProbMem.from_json(mem) for mem in mems]
            for carrier, mems in mem_data.items()
        }
        return instance


