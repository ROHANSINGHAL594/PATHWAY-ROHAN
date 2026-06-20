import pathway as pw
from tdigest import TDigest
from typing import List, Optional, Any, Dict
from .helpers import get_this_col


def make_tdigest_percentile_reducer(percentile: float):
    """
    Returns a reducer that computes the requested percentile.
    Example: reducer = make_tdigest_percentile_reducer(95.0)
    """


    class TDigestAccumulator(pw.BaseCustomAccumulator):
        def __init__(self, digest: TDigest):
            # Store the underlying t-digest
            self.digest = digest

        @classmethod
        def from_row(cls, row: Any) -> "TDigestAccumulator":
            # row is expected to be a tuple (value,)
            (v,) = row
            d = TDigest()
            d.update(v)
            return cls(d)

        def update(self, other: "TDigestAccumulator") -> None:
            # Merge another accumulator into this one
            self.digest = self.digest + other.digest

        def compute_result(self) -> float:
            """
            Return a dictionary mapping each requested percentile (0-100) 
            to its approximate value.
            """
            return self.digest.percentile(percentile)

    return pw.reducers.udf_reducer(TDigestAccumulator)

custom_reducers = {
    "p90":  make_tdigest_percentile_reducer(90),
    "p95":  make_tdigest_percentile_reducer(95),
    "p99":  make_tdigest_percentile_reducer(99),
}