"""Every 2x2 table compatible with a published agreement statistic."""
from ._core import (Enum2x2Error, InvalidInput, UndefinedStatistic,
                    expected_agreement, kappa_from_cells, kappa_max, kappa_min,
                    rounding_interval, rounds_to)
from ._recover import (IMPOSSIBLE, INFEASIBLE, INSUFFICIENT, SET, UNIQUE,
                       Recovery, Table, recover, recover_many)

__all__ = ["recover", "recover_many", "Recovery", "Table",
           "UNIQUE", "SET", "INFEASIBLE", "INSUFFICIENT", "IMPOSSIBLE",
           "Enum2x2Error", "InvalidInput", "UndefinedStatistic",
           "kappa_from_cells", "kappa_max", "kappa_min",
           "expected_agreement", "rounding_interval", "rounds_to"]
__version__ = "0.1.0"
