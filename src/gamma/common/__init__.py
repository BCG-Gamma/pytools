"""
Global definitions of basic types and functions for use across all gamma libraries
"""
from . import licensing as _licensing
from ._common import *

__version__ = "1.3.0rc1"
_licensing.check_license(__package__)
