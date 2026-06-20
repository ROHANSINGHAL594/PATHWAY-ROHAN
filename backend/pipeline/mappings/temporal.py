from typing import List
import pathway as pw
from lib.tables import AsofJoinNode, IntervalJoinNode, WindowJoinNode, WindowByNode
from .helpers import MappingValues, get_col, get_this_col, select_for_join
from .open_tel.prefix import is_special_column
from .transforms import _join
import json
from .custom_reducers import custom_reducers


def asof_join(inputs: List[pw.Table], node: AsofJoinNode):
    params = _join(inputs, node)
    left, right = inputs
    return left.asof_join(
        right,
        get_col(left, node.time_col1),
        get_col(right, node.time_col2),
        *params["expression"],
        how=params["how_map"][node.how],
    ).select(
        **select_for_join(
            left,
            right,
            params["same_joined_on"] + [node.time_col1] if node.time_col1 == node.time_col2 else [],
            node.how
        )
    )

def interval_join(inputs: List[pw.Table], node: IntervalJoinNode):
    params = _join(inputs, node)
    left, right = inputs
    return left.interval_join(
        right,
        get_col(left, node.time_col1),
        get_col(right, node.time_col2),
        pw.temporal.interval(node.lower_bound, node.upper_bound),
        *params["expression"],
        how=params["how_map"][node.how],
    ).select(
        **select_for_join(
            left,
            right,
            params["same_joined_on"] + [node.time_col1] if node.time_col1 == node.time_col2 else [],
            node.how
        )
    )

def window_join(inputs: List[pw.Table], node: WindowJoinNode):
    params = _join(inputs, node)
    left, right = inputs
    kwargs = node.model_dump()["window"]
    window_type = kwargs.pop("window_type")
    window = getattr(pw.temporal, window_type)(**kwargs)
    return left.window_join(
        right,
        get_col(left, node.time_col1),
        get_col(right, node.time_col2),
        window,
        *params["expression"],
        how=params["how_map"][node.how],
    ).select(
        **select_for_join(
            left,
            right,
            params["same_joined_on"] + [node.time_col1] if node.time_col1 == node.time_col2 else [],
            node.how
        )
    )

def window_by(inputs: List[pw.Table], node: WindowByNode):
    kwargs = node.model_dump()["window"]
    window_type = kwargs.pop("window_type")
    window = getattr(pw.temporal, window_type)(**kwargs)
    instance = get_this_col(node.instance_col) if node.instance_col is not None else None

    reduce_kwargs = {}
    if instance is not None:
        reduce_kwargs[node.instance_col] = pw.this._pw_instance
    _reducers = [(red["col"], red["reducer"], red["new_col"]) for red in node.reducers]
    
    reducers = {}
    for prev_col, reducer, new_col in _reducers:
        if hasattr(pw.reducers,reducer):
            reducers[new_col] = getattr(pw.reducers, reducer)(get_this_col(prev_col))   
        else:
            reducers[new_col] = custom_reducers[reducer](get_this_col(prev_col))
    return inputs[0].windowby(
        get_this_col(node.time_col),
        window=window,
        instance=instance
    ).reduce(
        pw.this._pw_window_start,
        pw.this._pw_window_end,
        **reducers,
        **{
            f"_pw_windowed_{col}" : pw.reducers.tuple(get_this_col(col)) for col in inputs[0].column_names() if col != node.instance_col and is_special_column(col)
        },
        **reduce_kwargs
    )

temporal_mappings: dict[str, MappingValues] = {
    "window_by": {
        "node_fn": window_by,
        "stringify": lambda node, inputs: f"Groups {inputs[0]} by {json.dumps(node.window)} window on {node.time_col}{'' if node.instance_col is None else f' with instance column {node.instance_col}'} and reduces with {', '.join([reducer['new_col'] + ' = ' +  reducer['reducer'] + '('+ reducer['col'] + ')' for reducer in node.reducers])}"
    },
    "asof_join": {
        "node_fn": asof_join,
        "stringify": lambda node, inputs: f"{node.how.upper()} ASOF Joins {inputs[0]} with {inputs[1]} on time columns {node.time_col1} and {node.time_col2} (direction: {node.direction})",
    },
    "interval_join": {
        "node_fn": interval_join,
        "stringify": lambda node, inputs: f"{node.how.upper()} Interval Joins {inputs[0]} with {inputs[1]} on {node.time_col1} and {node.time_col2} within bounds [{node.lower_bound}, {node.upper_bound}]",
    },
    "window_join": {
        "node_fn": window_join,
        "stringify": lambda node, inputs: f"{node.how.upper()} Window Joins {inputs[0]} with {inputs[1]} on {node.time_col1} and {node.time_col2} using {json.dumps(node.window)} window",
    },
}
