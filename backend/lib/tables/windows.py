from typing import List, Tuple, Optional, Literal, Union
from typing_extensions import TypedDict
from .base import TemporalNode, ReducerDict, TimedeltaType, DateTimeType

class CommonBehaviour(TypedDict):
    delay: Optional[TimedeltaType]
    cutoff: Optional[TimedeltaType]
    keep_results: bool

class Session(TypedDict):
    max_gap: TimedeltaType
    window_type: Literal["session"]

class Sliding(TypedDict):
    hop: TimedeltaType
    duration: TimedeltaType
    origin: DateTimeType
    window_type: Literal["sliding"]

class Tumbling(TypedDict):
    duration: TimedeltaType
    origin: Optional[DateTimeType]
    window_type: Literal["tumbling"]

class WindowByNode(TemporalNode):
    node_id: Literal["window_by"]
    n_inputs: Literal[1] = 1
    time_col: str
    instance_col: Optional[str] = None
    window: Union[Session, Sliding, Tumbling]
    behaviour: Optional[CommonBehaviour] = None
    reducers: List[ReducerDict]
