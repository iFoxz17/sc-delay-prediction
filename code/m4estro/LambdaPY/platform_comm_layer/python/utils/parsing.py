from typing import Set, Dict, Optional, TypeVar, Type, Any, Callable
from pydantic import TypeAdapter

from logger import get_logger
logger = get_logger(__name__)

T = TypeVar("T")

def parse_as(type_: Type[T], obj: Dict[str, Any]) -> T:
    adapter = TypeAdapter(type_)
    return adapter.validate_python(obj)

def get_query_params(query_params: Dict[str, str], allowed_keys: Optional[Set[str]] = None) -> Dict[str, str]:
    logger.debug(f"Initial query parameters: {query_params}: filtering with allowed keys: {allowed_keys}")

    if allowed_keys is not None:
        query_params = {
            k: v for k, v in query_params.items()
            if k in allowed_keys and v 
        }
    return query_params

def parse_id_list(csv: str) -> Set[int]:
    results: Set[int] = set()
    for token in csv.split(','):
        token: str = token.strip()
        if token:
            try:
                results.add(int(token))
            except ValueError:
                logger.warning(f"Invalid ID encountered: {token}")
    return results

def parse_str_list(csv: str, case: Optional[str] = 'lower', separator: str = ',') -> Set[str]:
    apply_case: Callable[[str], str] = (
        str.lower if case == 'lower'
        else str.upper if case == 'upper'
        else (lambda x: x)
    )
    return {apply_case(token.strip()) for token in csv.split(separator) if token.strip()}