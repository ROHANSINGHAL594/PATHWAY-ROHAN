from typing import List, Dict, Any
import pathway as pw
from lib.tables import JoinNode, FilterNode, GroupByNode, JSONSelectNode, FlattenNode, ArithmeticNode, ComparisonNode, BooleanNode
from .helpers import MappingValues, get_col, get_this_col, select_for_join
from .open_tel.prefix import is_special_column
from .custom_reducers import custom_reducers

# Operator mapping for filter node
_op_map = {
    ">": "__gt__",
    "<": "__lt__",
    "==": "__eq__",
    "!=": "__ne__",
    ">=": "__ge__",
    "<=": "__le__",
}

def _join(inputs: List[pw.Table], node: JoinNode) -> Dict[str, Any]:
    left, right = inputs
    expression = []
    same_joined = []
    for col1, col2 in node.on:
        if col1 == col2:
            same_joined.append(col1)
        col1 = get_col(left, col1)
        col2 = get_col(right, col2)
        expression.append(col1 == col2)
    how_map = {key: getattr(pw.JoinMode, key.upper()) for key in ["left", "right", "inner", "outer"]}

    return {
        'how_map': how_map,
        "expression": expression,
        "same_joined_on":  same_joined
    }

def asof_now_join(inputs: List[pw.Table], node):
    params = _join(inputs, node)
    left, right = inputs
    join_id = (left.id if node.join_id == "self" else right.id) if hasattr(node, "join_id") else None
    return left.asof_now_join(
        right,
        *params["expression"],
        how=params["how_map"][node.how],
        id=join_id
    ).select(
        **select_for_join(
            left,
            right,
            params["same_joined_on"],
            node.how
        ),
    )

def join(inputs: List[pw.Table], node: JoinNode):
    params = _join(inputs, node)
    left, right = inputs
    return left.join(
        right,
        *params["expression"],
        how=params["how_map"][node.how],
    ).select(
        **select_for_join(
            left,
            right,
            params["same_joined_on"],
            node.how
        ),
    )

def filter(inputs: List[pw.Table], node: FilterNode):
    args = True
    for filter in node.filters:
        col_name = filter["col"]
        op = filter["op"]
        value = filter["value"]
        col = get_this_col(col_name)
        if op in _op_map:
            args &= getattr(col, _op_map.get(op))(value)
        elif op == "contains":
            args &= col.str.find(value) != -1
        else:
            args &= getattr(col.str, op)(value)

    return inputs[0].filter(
        args
    )

def group_by(inputs: List[pw.Table], node: GroupByNode):
    table = inputs[0]
    
    # Build the groupby columns
    group_cols = [get_col(table, col) for col in node.columns]
    _reducers = [(red["col"], red["reducer"], red["new_col"]) for red in node.reducers ]
    reducers = {}
    for prev_col, reducer, new_col in _reducers:
        if hasattr(pw.reducers,reducer):
            reducers[new_col] = getattr(pw.reducers, reducer)(get_this_col(prev_col))   
        else:
            reducers[new_col] = custom_reducers[reducer](get_this_col(prev_col))

    for col in table.column_names():
        if col not in node.columns and is_special_column(col):
            reducers[f"_pw_grouped_{col}"] = pw.reducers.tuple(get_this_col(col))

    return table.groupby(*group_cols).reduce(*group_cols, **reducers)

def json_select(inputs: List[pw.Table], node: JSONSelectNode) -> pw.Table:
    table = inputs[0]
    new_column_name = node.new_column_name if node.new_column_name else node.property
    all_cols = [get_this_col(col) for col in table.column_names() if col != new_column_name]
    new_col = get_this_col(node.json_column)[node.property]

    if node.property_type != "json":
        new_col=pw.unwrap(getattr(new_col, f"as_{node.property_type}")())
        
    new_cols = {
        new_column_name: new_col
    }
    return table.select(
        *all_cols,
        **new_cols
    )

def flatten(inputs: List[pw.Table], node: FlattenNode) -> pw.Table:
    table = inputs[0]
    return table.flatten(get_this_col(node.column))


def arithmetic(inputs: List[pw.Table], node: ArithmeticNode) -> pw.Table:
    table = inputs[0]
    col_a = get_this_col(node.col_a)
    col_b = get_this_col(node.col_b)
    
    ops = {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "/": lambda a, b: a / b if b != 0 else None,
        "//": lambda a, b: a // b if b != 0 else None,
        "%": lambda a, b: a % b if b != 0 else None,
        "**": lambda a, b: a ** b,
    }
    
    res = ops[node.operator](col_a, col_b)
    
    all_cols = [get_this_col(col) for col in table.column_names() if col != node.new_col]
    
    return table.select(*all_cols, **{node.new_col: res})

def comparison(inputs: List[pw.Table], node: ComparisonNode) -> pw.Table:
    table = inputs[0]
    col_a = get_this_col(node.col_a)
    col_b = get_this_col(node.col_b)
    
    ops = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
    }
    
    res = ops[node.operator](col_a, col_b)
    
    all_cols = [get_this_col(col) for col in table.column_names() if col != node.new_col]
    
    return table.select(*all_cols, **{node.new_col: res})

def boolean(inputs: List[pw.Table], node: BooleanNode) -> pw.Table:
    table = inputs[0]
    col_a = get_this_col(node.col_a)
    
    ops = {
        "&": lambda a, b: a & b,
        "|": lambda a, b: a | b,
        "^": lambda a, b: a ^ b,
        "~": lambda a, b: ~a,
    }
    
    if node.operator == "~":
        res = ops[node.operator](col_a, None)
    else:
        col_b = get_this_col(node.col_b)
        res = ops[node.operator](col_a, col_b)
    
    all_cols = [get_this_col(col) for col in table.column_names() if col != node.new_col]
    
    return table.select(*all_cols, **{node.new_col: res})


transform_mappings: dict[str, MappingValues] = {
    "filter": {
        "node_fn": filter,
        "stringify": lambda node, inputs: f"Filters input {inputs[0]} where '{' and '.join([' '.join([filter['col'], filter['op'], str(filter['value'])]) for filter in node.filters])}'",
    },
    "join": {
        "node_fn": join,
        "stringify": lambda node, inputs: f"{node.how.upper()} Joins input {inputs[0]} with {inputs[1]} on {' AND '.join([f'{left}=={right}' for left, right in node.on])}",
    },
    "asof_now_join": {
        "node_fn": asof_now_join,
        "stringify": lambda node,inputs : f"{node.how.upper()} ASOF Now Joins input {inputs[0]} with {inputs[1]} on {' AND '.join([f'{left}=={right}' for left, right in node.on])}",
    },
    "group_by": {
        "node_fn": group_by,
        "stringify": lambda node, inputs: f"Groups input {inputs[0]} by {', '.join(node.columns)} and reduces with {', '.join([reducer['new_col'] + ' = ' +  reducer['reducer'] + '('+ reducer['col'] + ')' for reducer in node.reducers])}",
    },
    "json_select": {
        "node_fn": json_select,
        "stringify": lambda node, inputs: f"Selects attribute {node.property} from JSON column {node.json_column}{f' and stores it in column {node.new_column_name}' if node.new_column_name else ''} in input {inputs[0]}"
    },
    "flatten": {
        "node_fn": flatten,
        "stringify": lambda node,inputs: f"Flattens iterable column {node.column}, while retaining the column name, in input {inputs[0]}"
    },
    "arithmetic": {
        "node_fn": arithmetic,
        "stringify": lambda node, inputs: f"Calculates {node.new_col} = {node.col_a} {node.operator} {node.col_b} in input {inputs[0]}"
    },
    "comparison": {
        "node_fn": comparison,
        "stringify": lambda node, inputs: f"Compares {node.new_col} = {node.col_a} {node.operator} {node.col_b} in input {inputs[0]}"
    },
    "boolean": {
        "node_fn": boolean,
        "stringify": lambda node, inputs: f"Calculates {node.new_col} = {node.operator}{node.col_a}" if node.operator == "~" else f"Calculates {node.new_col} = {node.col_a} {node.operator} {node.col_b} in input {inputs[0]}"
    }
}
