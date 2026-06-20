from typing import Union, Literal
from typing_extensions import TypedDict
from datetime import datetime, timedelta
from ..node import Node

TimedeltaType = Union[int, float, timedelta, None]
DateTimeType = int | float | datetime | None

Reducer = Literal["any", "argmax", "argmin", "avg", "count", "count_distinct", "count_distinct_approximate", "earliest", "latest", "max", "min", "ndarray", "sorted_tuple", "stateful_many", "stateful_single", "sum", "tuple", "unique", "p90", "p95", "p99"]

class TableNode(Node):
    category: Literal["table"]

class TemporalNode(TableNode):
    category: Literal["temporal"]

class ReducerDict(TypedDict):
    col: str
    reducer: Reducer
    new_col : str