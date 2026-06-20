from typing import List, Union, Tuple, Any, Optional, Literal
from pydantic import Field
from .base import TableNode

JoinMode = Literal["left", "right", "inner", "outer"]
class _Join(TableNode):
    n_inputs: Literal[2] = 2
    on: List[Union[Tuple[str, str]]] = Field(default_factory=list)
    how: JoinMode
    left_exactly_once: Optional[bool] = False
    right_exactly_once: Optional[bool] = False

class JoinNode(_Join):
    node_id: Literal["join"]

class AsofNowJoinNode(_Join):
    node_id: Literal['asof_now_join']
    join_id: Optional[Literal["self", "other"]]

