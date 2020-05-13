"""
Core implementation of :mod:`gamma.common`
"""

import logging
import warnings
from functools import wraps
from typing import *

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


__all__ = ["is_list_like", "deprecated", "deprecation_warning", "AllTracker"]


class AllTracker:
    """
    Track global symbols defined in a module and validate that all eligible symbols have
    been included in the `__all__` variable.

    Eligible symbols are all symbols starting with a letter, but not with "Base".
    """

    def __init__(self, globals_: Dict[str, Any]):
        self.globals_ = globals_
        self.imported = set(globals_.keys())

    def validate(self) -> None:
        """
        Validate that all eligible symbols defined since creation of this tracker
        are listed in the `__all__` field.

        :raise RuntimeError: if `__all__` is not as expected
        """
        all_expected = [
            item
            for item in self.globals_
            if item[0].isalpha()
            and item not in self.imported
            and not item.startswith("Base")
        ]
        if set(self.globals_.get("__all__", [])) != set(all_expected):
            raise RuntimeError(
                f"unexpected all declaration, expected:\n__all__ = {all_expected}"
            )


__tracker = AllTracker(globals())
# we forget that class AllTracker itself is already defined, because we want to include
# it in the __all__ statement
__tracker.imported.remove(AllTracker.__name__)


def is_list_like(obj: Any) -> bool:
    """
    Check if the object is list-like.

    Objects that are considered list-like when they implement methods `len` and
    `__getitem__`. These include, for example, lists, tuples, sets, NumPy arrays, and
    Pandas series and indices.

    As an exception, the following types are not considered list-like despite
    implementing the methods above:

    - `str`
    - `bytes`
    - :class:`pandas.DataFrame`: inconsistent behaviour of the sequence interface; \
        iterating a data frame yields the values of the column index, while the length \
        of a data frame is its number of rows
    - :class:`pandas.Panel`: similar behaviour as for data frames
    - :class:`numpy.ndarray` instances with 0 dimensions


    :param obj The object to check
    :return `True` if `obj` has list-like properties
    """

    return (
        hasattr(obj, "__len__")
        and hasattr(obj, "__getitem__")
        and not isinstance(obj, (str, bytes, pd.DataFrame, pd.Panel))
        # exclude zero-dimensional numpy arrays, effectively scalars
        and not (isinstance(obj, np.ndarray) and obj.ndim == 0)
    )


def deprecated(function: Callable = None, *, message: str = None):
    """
    Decorator to mark functions as deprecated.

    It will result in a warning being logged when the function is used.

    To deprecate classes, apply this decorator to the `__init__` method, not to the
    class itself.
    """

    def _deprecated_inner(func: callable) -> callable:
        @wraps(func)
        def new_func(*args, **kwargs) -> Any:
            """
            Function wrapper
            """
            message_header = (
                f"Call to deprecated {type(func).__name__} {func.__qualname__}"
            )
            if message is None:
                warnings.warn(message_header, FutureWarning, stacklevel=2)
            else:
                warnings.warn(
                    f"{message_header}: {message}", FutureWarning, stacklevel=2
                )
            return func(*args, **kwargs)

        return new_func

    if function is None:
        return _deprecated_inner
    elif callable(function):
        return _deprecated_inner(function)
    elif isinstance(function, str):
        raise ValueError(
            "Deprecation message not provided as a keyword argument. "
            'Usage: @deprecated(message="...")'
        )
    else:
        raise ValueError("Deprecated object must be callable")


def deprecation_warning(message: str, stacklevel: int = 1) -> None:
    """
    Issue a deprecation warning.

    :param message: the warning message
    :param stacklevel: stack level relative to caller for emitting the context of the \
        warning (default: 1)
    :return:
    """
    if stacklevel < 1:
        raise ValueError(f"arg stacklevel={stacklevel} must be a positive integer")
    warnings.warn(message, FutureWarning, stacklevel=stacklevel + 1)


__tracker.validate()
