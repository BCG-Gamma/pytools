"""
String representations of expressions
"""

import logging
from typing import *

from gamma.common import AllTracker
from gamma.common.expression._expression import Expression, ExpressionFormatter

log = logging.getLogger(__name__)

INDENT_WIDTH = 4
MAX_LINE_LENGTH = 80

LEFT_ALIGNED_OPERATORS = {",", ":"}

__all__ = ["TextualForm", "PythonExpressionFormat"]
__tracker = AllTracker(globals())


class _IndentedLine(NamedTuple):
    """
    An indented line of text
    """

    indent: int
    text: str


class TextualForm:
    """
    A hierarchical textual representation of an expression
    """

    PADDING_NONE = "none"
    PADDING_RIGHT = "right"
    PADDING_BOTH = "both"

    __PADDING_SPACES = {PADDING_NONE: 0, PADDING_RIGHT: 1, PADDING_BOTH: 2}

    def __init__(self, expression: Expression, encapsulate: bool = False) -> None:
        subexpressions = expression.subexpressions
        multiple_subexpressions = len(subexpressions) > 1

        sub_forms = tuple(
            TextualForm(
                subexpression,
                encapsulate=(
                    multiple_subexpressions
                    and subexpression.precedence()
                    > expression.precedence() - (0 if pos == 0 else 1)
                ),
            )
            for pos, subexpression in enumerate(subexpressions)
        )

        brackets = expression.brackets
        assert brackets is None or len(brackets) == 2, "brackets is None or a pair"

        if not brackets and encapsulate:
            brackets = ("(", ")")

        infix = expression.infix
        prefix = expression.prefix

        infix_padding = (
            TextualForm.PADDING_RIGHT
            if infix in LEFT_ALIGNED_OPERATORS
            else TextualForm.PADDING_BOTH
        )

        # promote inner brackets to top level if inner is a bracketed singleton
        if not brackets and len(sub_forms) == 1:
            _inner_single = sub_forms[0]
            if not _inner_single.prefix:
                brackets = _inner_single.brackets
                sub_forms = _inner_single.inner

        self.prefix = prefix
        self.brackets = brackets
        self.infix = infix
        self.infix_padding = infix_padding
        self.inner = sub_forms

        self.__len = (
            len(prefix)
            + (len(brackets[0]) + len(brackets[1]) if brackets else 0)
            + sum(len(inner_representation) for inner_representation in sub_forms)
            + max(len(sub_forms) - 1, 0)
            * (len(infix) + (TextualForm.__PADDING_SPACES[infix_padding]))
        )

    def to_string(self, multiline: bool = True) -> str:
        """
        Convert this representation to a string
        :param multiline: if `True`, include line breaks to keep the width within \
            maximum bounds (default: `True`)
        :return: this representation rendered as a string
        """

        if multiline:

            def _spacing(indent: int) -> str:
                return " " * (INDENT_WIDTH * indent)

            return "\n".join(
                f"{_spacing(indent)}{text}" for indent, text in self._to_lines()
            )

        else:
            return self._to_single_line()

    @property
    def opening_bracket(self) -> str:
        """
        The opening bracket of this expression.
        """
        return self.brackets[0] if self.brackets else ""

    @property
    def closing_bracket(self) -> str:
        """
        The closing bracket of this expression.
        """
        return self.brackets[1] if self.brackets else ""

    def _to_lines(
        self, indent: int = 0, leading_characters: int = 0, trailing_characters: int = 0
    ) -> List[_IndentedLine]:
        """
        Convert this representation to as few lines as possible without exceeding
        maximum line length
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """

        if (
            leading_characters + len(self) + indent * INDENT_WIDTH + trailing_characters
            > MAX_LINE_LENGTH
        ):
            return self._to_multiple_lines(
                indent=indent,
                leading_characters=leading_characters,
                trailing_characters=trailing_characters,
            )
        else:
            return [_IndentedLine(indent=indent, text=self._to_single_line())]

    def _to_single_line(self) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        if self.infix:
            infix_padding = self.infix_padding
            if infix_padding is TextualForm.PADDING_NONE:
                infix = self.infix
            elif infix_padding is TextualForm.PADDING_RIGHT:
                infix = f"{self.infix} "
            elif infix_padding is TextualForm.PADDING_BOTH:
                infix = f" {self.infix} "
            else:
                raise ValueError(f"unknown infix padding: {infix_padding}")
        else:
            infix = ""
        inner = infix.join(
            subexpression_representation._to_single_line()
            for subexpression_representation in self.inner
        )
        return f"{self.prefix}{self.opening_bracket}{inner}{self.closing_bracket}"

    def _to_multiple_lines(
        self, indent: int, leading_characters: int, trailing_characters: int
    ) -> List[_IndentedLine]:
        """
        Convert this representation to multiple lines
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """

        result: List[_IndentedLine] = []

        inner: Tuple[TextualForm, ...] = self.inner

        # we add parentheses if there is no existing bracketing, and either
        # - there is a prefix, or
        # - we are at indentation level 0 and have more than one inner element
        parenthesize = not self.brackets and (
            self.prefix or (indent == 0 and len(inner) > 1)
        )

        if parenthesize:
            opening_bracket = f"{self.prefix}("
        else:
            opening_bracket = f"{self.prefix}{self.opening_bracket}"

        if opening_bracket:
            result.append(_IndentedLine(indent=indent, text=opening_bracket))
            inner_indent = indent + 1
        else:
            inner_indent = indent

        if len(inner) == 1:
            inner_single = inner[0]

            result.extend(
                inner_single._to_lines(
                    indent=inner_indent,
                    leading_characters=leading_characters,
                    trailing_characters=trailing_characters,
                )
            )

        elif inner:

            last_idx = len(inner) - 1
            infix = self.infix

            if self.infix_padding is TextualForm.PADDING_RIGHT:
                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = inner_representation._to_lines(
                        indent=inner_indent,
                        leading_characters=(leading_characters if idx == 0 else 0),
                        trailing_characters=(
                            len_infix if idx < last_idx else trailing_characters
                        ),
                    )

                    if idx != last_idx:
                        # append infix to last line,
                        # except we're in the last representation
                        lines[-1] = _IndentedLine(
                            indent=inner_indent, text=f"{lines[-1].text}{infix}"
                        )

                    result.extend(lines)
            else:
                if self.infix_padding is TextualForm.PADDING_BOTH:
                    infix = f"{infix} "

                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = inner_representation._to_lines(
                        indent=inner_indent,
                        leading_characters=leading_characters
                        if idx == 0
                        else len_infix,
                        trailing_characters=(
                            trailing_characters if idx == last_idx else 0
                        ),
                    )
                    if idx != 0:
                        # prepend infix to first line,
                        # except we're in the first representation
                        lines[0] = _IndentedLine(
                            indent=inner_indent, text=f"{infix}{lines[0].text}"
                        )

                    result.extend(lines)

        if parenthesize:
            closing_bracket = f")"
        else:
            closing_bracket = f"{self.closing_bracket}"

        if closing_bracket:
            result.append(_IndentedLine(indent=indent, text=closing_bracket))

        return result

    def __repr__(self) -> str:
        return self.to_string()

    def __len__(self) -> int:
        return self.__len


class PythonExpressionFormat(ExpressionFormatter):
    """
    Formats expression objects as Python expressions, in line with the `black` style
    """

    def to_text(self, expression: "Expression") -> str:
        """[see superclass]"""
        return TextualForm(expression).to_string()

    to_text.__doc__ = ExpressionFormatter.to_text.__doc__


# Register class PythonExpressionFormat as the default display form
# noinspection PyProtectedMember
ExpressionFormatter._register_default_format(PythonExpressionFormat())

__tracker.validate()
