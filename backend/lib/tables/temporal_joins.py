from typing import Union, Optional, Literal
from datetime import timedelta
from .joins import _Join
from .windows import CommonBehaviour, Session, Sliding, Tumbling

class TemporalJoinNode(_Join):
    category: Literal["temporal"]
    time_col1: str
    time_col2: str
    left_exactly_once: Optional[None] = None
    right_exactly_once: Optional[None] = None

class AsofJoinNode(TemporalJoinNode):
    node_id: Literal["asof_join"]
    direction: Literal["backward", "forward", "nearest"]
    behaviour: Optional[CommonBehaviour] = None

class IntervalJoinNode(TemporalJoinNode):
    node_id: Literal["interval_join"]
    lower_bound: Union[timedelta, int]
    upper_bound: Union[timedelta, int]

class WindowJoinNode(TemporalJoinNode):
    node_id: Literal["window_join"]
    window: Union[Session, Sliding, Tumbling]
