import logging
from abc import ABCMeta, abstractmethod
from typing import Mapping, Set, Tuple

from gamma.common import AllTracker

log = logging.getLogger(__name__)

__all__ = [
    "Operator",
    "BinaryOperator",
    "UnaryOperator",
    "DOT",
    "POW",
    "POS",
    "NEG",
    "MUL",
    "MATMUL",
    "DIV",
    "TRUE_DIV",
    "FLOOR_DIV",
    "INVERT",
    "MOD",
    "ADD",
    "SUB",
    "LSHIFT",
    "RSHIFT",
    "AND_BITWISE",
    "XOR_BITWISE",
    "OR_BITWISE",
    "IN",
    "NOT_IN",
    "IS",
    "IS_NOT",
    "LT",
    "LE",
    "GT",
    "GE",
    "NEQ_",
    "NEQ",
    "EQ",
    "NOT",
    "AND",
    "OR",
    "LAMBDA",
    "ASSIGN",
    "COLON",
    "COMMA",
    "NONE",
    "OPERATOR_PRECEDENCE",
    "MAX_PRECEDENCE",
    "MIN_PRECEDENCE",
]

__tracker = AllTracker(globals_=globals())


class Operator(metaclass=ABCMeta):
    """
    Base class for operators used in expressions
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    @abstractmethod
    def is_unary(self) -> bool:
        """
        `True` if this is a unary operator
        """
        pass

    def __eq__(self, other: "Operator") -> bool:
        return type(self) == type(other) and self.symbol == other.symbol

    def __hash__(self) -> int:
        return hash(type(self)) + 3 * hash(self.symbol)


class BinaryOperator(Operator):
    """
    A binary operator
    """

    @property
    def is_unary(self) -> bool:
        """[see superclass]"""
        return False

    is_unary.__doc__ = Operator.is_unary.__doc__


class UnaryOperator(Operator):
    """
    A unary rator
    """

    @property
    def is_unary(self) -> bool:
        """[see superclass]"""
        return True

    is_unary.__doc__ = Operator.is_unary.__doc__


DOT = BinaryOperator(".")
POW = BinaryOperator("**")
POS = UnaryOperator("+")
NEG = UnaryOperator("-")
MUL = BinaryOperator("*")
MATMUL = BinaryOperator("@")
DIV = TRUE_DIV = BinaryOperator("/")
FLOOR_DIV = BinaryOperator("//")
INVERT = UnaryOperator("~")
MOD = BinaryOperator("%")
ADD = BinaryOperator("+")
SUB = BinaryOperator("-")
LSHIFT = BinaryOperator("<<")
RSHIFT = BinaryOperator(">>")
AND_BITWISE = BinaryOperator("&")
XOR_BITWISE = BinaryOperator("^")
OR_BITWISE = BinaryOperator("|")
IN = BinaryOperator("in")
NOT_IN = BinaryOperator("not in")
IS = BinaryOperator("is")
IS_NOT = BinaryOperator("is not")
LT = BinaryOperator("<")
LE = BinaryOperator("<=")
GT = BinaryOperator(">")
GE = BinaryOperator(">=")
NEQ_ = BinaryOperator("<>")
NEQ = BinaryOperator("!=")
EQ = BinaryOperator("==")
NOT = UnaryOperator("not")
AND = BinaryOperator("and")
OR = BinaryOperator("or")
LAMBDA = UnaryOperator("lambda")
ASSIGN = BinaryOperator("=")
COLON = BinaryOperator(":")
COMMA = BinaryOperator(",")
NONE = BinaryOperator("")


__OPERATOR_PRECEDENCE_ORDER: Tuple[Set[Operator], ...] = (
    {DOT},
    {POW},
    {INVERT},
    {POS, NEG},
    {MUL, MATMUL, DIV, FLOOR_DIV, MOD},
    {ADD, SUB},
    {LSHIFT, RSHIFT},
    {AND_BITWISE},
    {XOR_BITWISE},
    {OR_BITWISE},
    {IN, NOT_IN, IS, IS_NOT, LT, LE, GT, GE},
    {NEQ_, NEQ, EQ},
    {NOT},
    {AND},
    {OR},
    {LAMBDA},
    {ASSIGN, COLON},
    {COMMA},
)
OPERATOR_PRECEDENCE: Mapping[Operator, int] = {
    operator: priority
    for priority, operators in enumerate(__OPERATOR_PRECEDENCE_ORDER)
    for operator in operators
}
MAX_PRECEDENCE = -1
MIN_PRECEDENCE = len(__OPERATOR_PRECEDENCE_ORDER)


__tracker.validate()
