"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
from __future__ import annotations

import itertools
import logging
from abc import ABCMeta, abstractmethod
from typing import *
from typing import List

log = logging.getLogger(__name__)

__all__ = [
    "IndentedLine",
    "ExpressionRepresentation",
    "Expression",
    "Literal",
    "Identifier",
    "Operation",
    "UnaryOperation",
    "Enumeration",
    "Function",
]

INDENT_WIDTH = 4
MAX_LINE_LENGTH = 15

__OPERATOR_PRECEDENCE_ORDER = (
    {"."},
    {"**"},
    {"~"},
    {"+ x", "- x"},
    {"*", "/", "//", "%"},
    {"+", "-"},
    {"<<", ">>"},
    {"&"},
    {"^"},
    {"|"},
    {"in", "not in", "is", "is not", "<", "<=", ">", ">="},
    {"<>", "!=", "=="},
    {"not x"},
    {"and"},
    {"or"},
    {"lambda"},
    {"="},
    {","},
)

OPERATOR_PRECEDENCE = {
    operator: priority
    for priority, operators in enumerate(__OPERATOR_PRECEDENCE_ORDER)
    for operator in operators
}

MAX_PRECEDENCE = len(__OPERATOR_PRECEDENCE_ORDER)


class IndentedLine(NamedTuple):
    """
    An indented line of text
    """

    indent: int
    text: str


class ExpressionRepresentation:
    """
    A hierarchical string representation of an expression
    """

    def __init__(
        self,
        prefix: str = "",
        *,
        infix: str = "",
        infix_leading_space: bool = True,
        inner: Tuple[ExpressionRepresentation, ...] = (),
        suffix: str = "",
    ):
        """
        :param prefix: the start of the expression
        :param infix: separator for subexpressions nested inside the expression
        :param infix_leading_space: if `True`, the infix operator has spaces on both \
            sides, otherwise has a space only on the right
        :param inner: list of representations of the subexpressions nested inside the \
            expression
        :param suffix: the end of the expression
        """
        self.prefix = prefix
        self.infix = infix
        self.infix_leading_space = infix_leading_space
        self.inner = inner
        self.suffix = suffix
        infix_length = len(infix) + (2 if infix_leading_space else 1)
        self.__len = (
            len(prefix)
            + sum(len(inner_representation) for inner_representation in inner)
            + max(len(inner) - 1, 0) * infix_length
            + len(suffix)
        )

    def with_wrapper(self, prefix: str, suffix: str) -> ExpressionRepresentation:
        """
        Construct a copy of this representation with a new prefix and suffix
        :param prefix: the new prefix
        :param suffix: the new suffix
        :return: the new representation
        """
        return ExpressionRepresentation(
            prefix=prefix,
            infix=self.infix,
            infix_leading_space=self.infix_leading_space,
            inner=self.inner,
            suffix=suffix,
        )

    def _to_lines(
        self, indent: int = 0, leading_space: int = 0, trailing_space: int = 0
    ) -> List[IndentedLine]:
        """
        Convert this representation to as few lines as possible without exceeding
        maximum line length
        :param indent: global indent of this expression
        :param leading_space: leading space to reserve in first line
        :param trailing_space: trailing space to reserve in last line
        :return: resulting lines
        """
        log.warning(
            (
                self._to_single_line(),
                indent * INDENT_WIDTH,
                leading_space,
                len(self),
                trailing_space,
            )
        )

        if (
            leading_space + len(self) + indent * INDENT_WIDTH + trailing_space
            > MAX_LINE_LENGTH
        ):
            return self._to_multiple_lines(
                indent=indent,
                leading_space=leading_space,
                trailing_space=trailing_space,
            )
        else:
            return [IndentedLine(indent=indent, text=self._to_single_line())]

    def _to_single_line(self) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        if self.infix:
            if self.infix_leading_space:
                infix = f" {self.infix} "
            else:
                infix = f"{self.infix} "
        else:
            infix = ""
        inner = infix.join(
            subexpression_representation._to_single_line()
            for subexpression_representation in self.inner
        )
        return f"{self.prefix}{inner}{self.suffix}"

    def _to_multiple_lines(
        self, indent: int, leading_space: int, trailing_space: int
    ) -> List[IndentedLine]:
        """
        Convert this representation to multiple lines
        :param indent: global indent of this expression
        :param leading_space: leading space to reserve in first line
        :param trailing_space: trailing space to reserve in last line
        :return: resulting lines
        """
        result: List[IndentedLine] = []
        if self.prefix:
            result.append(IndentedLine(indent=indent, text=self.prefix))
            inner_indent = indent + 1
        else:
            inner_indent = indent

        inner = self.inner
        if inner:
            infix = self.infix
            if infix:
                if self.infix_leading_space:
                    len_infix = len(infix) + 1
                    result.extend(
                        inner[0]._to_lines(
                            indent=inner_indent,
                            leading_space=leading_space,
                            trailing_space=0 if len(inner) > 1 else trailing_space,
                        )
                    )
                    for inner_representation in inner[1:]:
                        lines = inner_representation._to_lines(
                            indent=inner_indent,
                            leading_space=len_infix,
                            trailing_space=(
                                trailing_space
                                if inner_representation is inner[-1]
                                else 0
                            ),
                        )
                        result.append(
                            IndentedLine(
                                indent=inner_indent, text=f"{infix} {lines[0].text}"
                            )
                        )
                        result.extend(lines[1:])
                else:
                    len_infix = len(infix)
                    for inner_representation in inner[:-1]:
                        lines = inner_representation._to_lines(
                            indent=inner_indent,
                            leading_space=(
                                leading_space if inner_representation is inner[0] else 0
                            ),
                            trailing_space=len_infix,
                        )
                        result.extend(lines[:-1])
                        result.append(
                            IndentedLine(
                                indent=inner_indent, text=f"{lines[-1].text}{infix}"
                            )
                        )
                    result.extend(
                        inner[-1]._to_lines(
                            indent=inner_indent,
                            leading_space=leading_space if len(inner) == 1 else 0,
                            trailing_space=trailing_space,
                        )
                    )
            else:
                result.extend(
                    itertools.chain.from_iterable(
                        inner_representation._to_lines(indent=inner_indent)
                        for inner_representation in inner
                    )
                )
        if self.suffix:
            result.append(IndentedLine(indent=indent, text=self.suffix))
        return result

    def __str__(self) -> str:
        multiline = True

        def _spacing(indent: int) -> str:
            return " " * (INDENT_WIDTH * indent)

        lines: List[IndentedLine] = self._to_lines()
        if multiline:
            return "\n".join(f"{_spacing(indent)}{text}" for indent, text in lines)
        else:
            if len(lines) == 1:
                return lines[0].text
            else:
                return "".join(
                    f"{text} " if indent == next_indent else text
                    for (indent, text), next_indent in itertools.zip_longest(
                        lines, (indent for indent, _ in lines[1:])
                    )
                )

    def __len__(self) -> int:
        return self.__len


class Expression(metaclass=ABCMeta):
    """
    A nested expression
    """

    @abstractmethod
    def representation(self) -> ExpressionRepresentation:
        """
        Return a nested text representation of this expression
        """
        pass

    def _subexpression_representation(
        self, subexpression: Expression
    ) -> ExpressionRepresentation:
        subexpression_representation = subexpression.representation()
        if subexpression.precedence() >= self.precedence():
            if subexpression_representation.prefix:
                return ExpressionRepresentation(
                    prefix="(", inner=(subexpression_representation,), suffix=")"
                )
            else:
                return subexpression_representation.with_wrapper(prefix="(", suffix=")")
        else:
            return subexpression_representation

    def precedence(self) -> int:
        """
        :return: the precedence of this expression, used to determine the need for \
            parentheses
        """
        return -1

    def __repr__(self) -> str:
        return str(self.representation())

    def __add__(self, other: Expression) -> Operation:
        return Operation("+", (self, other))

    def __sub__(self, other: Expression) -> Operation:
        return Operation("-", (self, other))

    def __mul__(self, other: Expression) -> Operation:
        return Operation("*", (self, other))

    def __matmul__(self, other: Expression) -> Operation:
        return Operation("@", (self, other))

    def __truediv__(self, other: Expression) -> Operation:
        return Operation("/", (self, other))

    def __floordiv__(self, other: Expression) -> Operation:
        return Operation("//", (self, other))

    def __mod__(self, other: Expression) -> Operation:
        return Operation("%", (self, other))

    def __pow__(self, power, modulo=None) -> Operation:
        if modulo is not None:
            raise NotImplementedError("modulo is not supported")
        return Operation("**", (self, power))

    def __lshift__(self, other: Expression) -> Operation:
        return Operation("<<", (self, other))

    def __rshift__(self, other: Expression) -> Operation:
        return Operation(">>", (self, other))

    def __and__(self, other: Expression) -> Operation:
        return Operation("&", (self, other))

    def __xor__(self, other: Expression) -> Operation:
        return Operation("^", (self, other))

    def __or__(self, other: Expression) -> Operation:
        return Operation("|", (self, other))

    def __neg__(self) -> UnaryOperation:
        return UnaryOperation("-", self)

    def __pos__(self) -> UnaryOperation:
        return UnaryOperation("+", self)

    def __invert__(self) -> UnaryOperation:
        return UnaryOperation("~", self)


class Literal(Expression):
    """
    A literal
    """

    def __init__(self, value: Any):
        self.value = value

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(repr(self.value))

    representation.__doc__ = Expression.representation.__doc__


class Identifier(Expression):
    """
    An identifier
    """

    def __init__(self, name: str):
        if not isinstance(name, str):
            raise ValueError("arg name must be a string")
        self.name = name

    def __call__(self, *args: Expression, **kwargs: Expression) -> Function:
        return Function(name=self.name, *args, **kwargs)

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(self.name)

    representation.__doc__ = Expression.representation.__doc__


class BaseOperation(Expression, metaclass=ABCMeta):
    """
    Abstract base class for operation expressions
    """

    def __init__(self, operator: str) -> None:
        if len(operator.split()) > 1:
            raise ValueError("operator must not contain whitespace")
        self.operator = operator


class Operation(BaseOperation):
    """
    A operation with at least two operands
    """

    def __init__(self, operator: str, subexpressions: Tuple[Expression, ...]):
        super().__init__(operator=operator)
        if len(subexpressions) < 2:
            raise ValueError("need to pass at least two subexpressions")
        if not all(isinstance(expression, Expression) for expression in subexpressions):
            raise ValueError("all subexpressions must implement class Expression")

        first_subexpression = subexpressions[0]
        if (
            isinstance(first_subexpression, Operation)
            and first_subexpression.operator == operator
        ):
            # if first subexpression has the same operator, we flatten the subexpression
            self.subexpressions = (
                *first_subexpression.subexpressions,
                *subexpressions[1:],
            )
        else:
            self.subexpressions = subexpressions

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(self.operator, MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            infix=self.operator,
            inner=tuple(
                self._subexpression_representation(subexpression=subexpression)
                for subexpression in self.subexpressions
            ),
        )

    representation.__doc__ = Expression.representation.__doc__


class UnaryOperation(BaseOperation):
    """
    A unary operation
    """

    def __init__(self, operator: str, subexpression: Expression):
        super().__init__(operator=operator)
        if not isinstance(subexpression, Expression):
            raise ValueError("subexpression must implement class Expression")

        self.subexpression = subexpression

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(f"{self.operator} x", MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            prefix=self.operator,
            inner=(self._subexpression_representation(self.subexpression),),
        )

    representation.__doc__ = Expression.representation.__doc__


class Enumeration(Expression):
    """
    An enumeration of expressions, separated by commas
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE[","]

    def __init__(
        self,
        delimiter_left: str,
        elements: Tuple[Expression, ...],
        delimiter_right: str,
    ) -> None:
        if not all(isinstance(element, Expression) for element in elements):
            raise ValueError("all elements must implement class Expression")
        self.delimiter_left = delimiter_left
        self.delimiter_right = delimiter_right
        self.elements = elements

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        elements = self.elements
        return ExpressionRepresentation(
            prefix=self.delimiter_left,
            inner=tuple(
                self._subexpression_representation(element) for element in self.elements
            ),
            infix=",",
            infix_leading_space=False,
            suffix=self.delimiter_right,
        )

    representation.__doc__ = Expression.representation.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return self._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__


class _KeywordArgument(Operation):
    """
    A keyword argument, used by functions
    """

    def __init__(self, name: str, value: Expression):
        super().__init__(operator="=", subexpressions=(Identifier(name), value))


class Function(Enumeration):
    """
    A function invocation
    """

    def __init__(self, name: str, *args: Expression, **kwargs: Expression):
        super().__init__(
            delimiter_left=f"{name}(",
            elements=(
                *args,
                *(
                    _KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
            delimiter_right=")",
        )
        self.name = name


def main() -> None:
    """
    Basic tests
    Todo: convert into unit tests
    """
    e = Function(
        "f",
        (Literal(1) | Literal(2)) >> Literal("x") % Identifier("x"),
        abc=-Literal(5),
    )
    rep = str(e)
    print(len(rep))
    print(len(e.representation()))
    print(f'"{rep}"')


if __name__ == "__main__":
    main()
