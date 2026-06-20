from typing import Literal, List, Tuple, Optional
from typing_extensions import TypedDict
from .base import TableNode, ReducerDict

ops = Literal["==", "<", "<=", ">=", ">", "!=", "startswith", "endswith", "find"]


class Filter(TypedDict):
    col: str
    op: ops
    value: int | float | str

class FilterNode(TableNode):
    node_id: Literal["filter"]
    # col, operation, value
    filters: List[Filter]
    n_inputs: Literal[1] = 1

class GroupByNode(TableNode):
    node_id: Literal["group_by"]
    columns: List[str]
    # prev_col, reducer, new_col
    reducers: List[ReducerDict]
    n_inputs: Literal[1] = 1


class JSONSelectNode(TableNode):
    node_id: Literal["json_select"]
    json_column: str
    property: str | int
    property_type: Literal["json", "str", "int", "float", "bool"]
    new_column_name: Optional[str]
    n_inputs: Literal[1] = 1

class FlattenNode(TableNode):
    node_id : Literal["flatten"]
    column: str
    n_inputs: Literal[1] = 1

ArithmeticOps = Literal["+", "-", "*", "/", "//", "%", "**"]
class ArithmeticNode(TableNode):
    node_id: Literal["arithmetic"]
    col_a: str
    col_b: str
    operator: ArithmeticOps
    new_col: str
    n_inputs: Literal[1] = 1

ComparisonOps = Literal["==", "!=", ">", "<", ">=", "<="]
class ComparisonNode(TableNode):
    node_id: Literal["comparison"]
    col_a: str
    col_b: str
    operator: ComparisonOps
    new_col: str
    n_inputs: Literal[1] = 1

BooleanOps = Literal["&", "|", "^", "~"]
class BooleanNode(TableNode):
    node_id: Literal["boolean"]
    col_a: str
    col_b: Optional[str] = None
    operator: BooleanOps
    new_col: str
    n_inputs: Literal[1] = 1