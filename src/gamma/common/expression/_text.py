"""
String representations of expressions
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import *

import gamma.common.expression.operator as op
from gamma.common import AllTracker
from gamma.common.expression._expression import (
    AtomicExpression,
    BracketedExpression,
    BracketPair,
    BRACKETS_ROUND,
    EPSILON,
    Expression,
    ExpressionAlias,
    ExpressionFormatter,
    InfixExpression,
    PrefixExpression,
)

log = logging.getLogger(__name__)

__all__ = ["PythonExpressionFormatter"]


#
# Private helper classes
#


class FormattingConfig(NamedTuple):
    """
    The parameters to use for formatting an expression
    """

    max_width: int = 80
    """maximum line width"""
    indent_width: int = 4
    """number of spaces in one indentation"""
    single_line: bool = False
    """if `True`, always produce a single line regardless of width"""


class IndentedLine(NamedTuple):
    """
    An indented line of text
    """

    indent: int
    text: str

    def prepend(self, text: str) -> "IndentedLine":
        """
        Add the given text to the start of this indented line
        :param text: the text to add
        :return: a copy of this indented line, with the text added
        """
        return IndentedLine(indent=self.indent, text=text + self.text)

    def append(self, text: str) -> "IndentedLine":
        """
        Add the given text to the end of this indented line
        :param text: the text to add
        :return: a copy of this indented line, with the text added
        """
        return IndentedLine(indent=self.indent, text=self.text + text)

    def __add__(self, other: str) -> "IndentedLine":
        return self.append(text=other)

    def __radd__(self, other: str) -> "IndentedLine":
        return self.prepend(text=other)

    def __len__(self) -> int:
        return len(self.text)


class TextualForm:
    """
    A hierarchical textual representation of an expression
    """

    @staticmethod
    def from_expression(expression: Expression) -> "TextualForm":
        """
        Generate a textual form for the given expression
        :param expression: the expression to be transformed
        :return: the resulting textual form
        """
        if expression is EPSILON:
            return EMPTY_FORM
        if isinstance(expression, AtomicExpression):
            return AtomicForm(expression)
        elif isinstance(expression, BracketedExpression):
            return BracketedForm.from_bracketed_expression(expression)
        elif isinstance(expression, InfixExpression):
            return InfixForm.from_infix_expression(expression)
        elif isinstance(expression, PrefixExpression):
            return PrefixForm.from_prefix_expression(expression)
        elif isinstance(expression, ExpressionAlias):
            return TextualForm.from_expression(expression.expression_)
        else:
            raise TypeError(f"unknown expression type: {type(expression)}")

    @property
    def needs_multi_line_encapsulation(self) -> bool:
        """
        If `True`, this form should be encapsulated in brackets when rendered
        across multiple lines.
        """
        return False

    def to_text(self, config: FormattingConfig) -> str:
        """
        Render this textual form as a string
        :param config: the formatting configuration to use
        :return: the resulting string
        """

        if config.single_line:

            return self.to_single_line()

        else:

            def _spacing(indent: int) -> str:
                return " " * (config.indent_width * indent)

            return "\n".join(
                f"{_spacing(indent)}{text}"
                for indent, text in self.to_lines(config=config)
            )

    @abstractmethod
    def to_lines(
        self,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        """
        Generate a list of indented lines from this textual form.
        :param config: the rendering configuration
        :param indent: the indentation level to use as a starting point
        :param leading_characters: space to reserve in the first line for leading \
            characters (needed to determine whether maximum width has been exceeded)
        :param trailing_characters: space to reserve in the last line for trailing \
            characters (needed to determine whether maximum width has been exceeded)
        :return: a list of indented lines generated from this textual form
        """
        pass

    @abstractmethod
    def to_single_line(self) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        pass

    def encapsulate(
        self, *, condition: bool = True, single_line: bool = True
    ) -> "TextualForm":
        """
        Return this form encapsulated in round parentheses.
        :param condition: if `False`, do not encapsulate this form
        :param single_line: if `False`, render the encapsulation only when the form \
            is rendered across multiple lines
        :return: the resulting form depending on the condition
        """
        return (
            BracketedForm(
                brackets=BRACKETS_ROUND, subform=self, single_line=single_line
            )
            if condition
            else self
        )

    @abstractmethod
    def __len__(self) -> int:
        pass

    def __repr__(self) -> str:
        # noinspection PyProtectedMember
        return self.to_text(config=_DEFAULT_PYTHON_EXPRESSION_FORMATTER.config)


class EmptyForm(TextualForm):
    """
    An empty form representing the _epsilon_ expression.
    """

    def to_lines(
        self,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        """[see superclass]"""
        return []

    to_lines.__doc__ = TextualForm.to_lines.__doc__

    def to_single_line(self) -> str:
        """[see superclass]"""
        return ""

    to_single_line.__doc__ = TextualForm.to_single_line.__doc__

    def __len__(self) -> int:
        """[see superclass]"""
        return 0


EMPTY_FORM = EmptyForm()


class AtomicForm(TextualForm):
    """
    A textual representation of an atomic expression
    """

    def __init__(self, expression: AtomicExpression) -> None:
        self.text = expression.text_

    def to_lines(
        self,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        """[see superclass]"""

        return [IndentedLine(indent=indent, text=self.to_single_line())]

    to_lines.__doc__ = TextualForm.to_lines.__doc__

    def to_single_line(self) -> str:
        """[see superclass]"""

        return self.text

    to_single_line.__doc__ = TextualForm.to_single_line.__doc__

    def __len__(self) -> int:
        return len(self.text)


class ComplexForm(TextualForm, metaclass=ABCMeta):
    """
    Base class of non-atomic forms.
    """

    def __init__(self, length: int) -> None:
        """
        :param length: the length of the single-line representation of this form
        """

        self._len = length

    def to_lines(
        self,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        """[see superclass]"""

        if (
            leading_characters
            + len(self)
            + indent * config.indent_width
            + trailing_characters
            > config.max_width
        ):
            return self.to_multiple_lines(
                config=config,
                indent=indent,
                leading_characters=leading_characters,
                trailing_characters=trailing_characters,
            )
        else:
            return [IndentedLine(indent=indent, text=self.to_single_line())]

    @abstractmethod
    def to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:
        """
        Convert this representation to multiple lines.

        :param config: the formatting configuration to use
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """
        pass

    def __len__(self) -> int:
        return self._len


class BracketedForm(ComplexForm):
    """
    A hierarchical textual representation of a complex expression
    """

    def __init__(
        self, brackets: BracketPair, subform: TextualForm, single_line: bool = True
    ) -> None:
        """
        :param brackets: the brackets surrounding the subform(s)
        :param subform: the subform to be bracketed
        :param single_line: if `False`, do not render the brackets in single-line \
            output
        """

        super().__init__(
            length=(
                (len(brackets.opening) + len(brackets.closing)) if single_line else 0
            )
            + len(subform)
        )

        self.brackets = brackets
        self.subform = subform
        self.single_line = single_line

    @staticmethod
    def from_bracketed_expression(expression: BracketedExpression) -> "BracketedForm":
        """
        Make a bracketed from for the given bracketed expression
        :param expression: the bracketed expression to convert
        :return: the resulting bracketed form
        """
        return BracketedForm(
            brackets=expression.brackets_,
            subform=TextualForm.from_expression(expression.subexpression_),
        )

    def to_single_line(self) -> str:
        """[see superclass]"""
        subform_text = self.subform.to_single_line()
        if self.single_line:
            # render the brackets only when they are visible in single-line forms
            return f"{self.brackets.opening}{subform_text}{self.brackets.closing}"
        else:
            return subform_text

    to_single_line.__doc__ = TextualForm.to_single_line.__doc__

    def to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:
        """[see superclass]"""

        return [
            IndentedLine(indent=indent, text=self.brackets.opening),
            *self.subform.to_lines(
                config=config,
                indent=indent + 1,
                leading_characters=0,
                trailing_characters=0,
            ),
            IndentedLine(indent=indent, text=self.brackets.closing),
        ]

    to_multiple_lines.__doc__ = ComplexForm.to_multiple_lines.__doc__


class PrefixForm(ComplexForm):
    """
    A hierarchical textual representation of a complex expression
    """

    def __init__(self, prefix: TextualForm, separator: str, body: TextualForm) -> None:
        """
        :param prefix: the prefix form
        :param separator: characters separating the prefix from the subform
        :param body: the body form
        """
        super().__init__(length=len(prefix) + len(separator) + len(body))

        self.prefix = prefix
        self.separator = separator
        self.body = body

    @staticmethod
    def from_prefix_expression(expression: PrefixExpression) -> TextualForm:
        """
        Create a prefixed form from the given prefix expression
        """

        prefix = expression.prefix_
        prefix_form = TextualForm.from_expression(prefix).encapsulate(
            condition=prefix.precedence_ < expression.precedence_
        )

        body = expression.body_
        body_form = TextualForm.from_expression(body).encapsulate(
            condition=body.precedence_ < expression.precedence_
        )

        separator = expression.separator_
        if len(prefix_form) and separator[:1].isalpha():
            separator = " " + separator
        if len(body_form) and separator[-1:].isalpha():
            separator += " "

        return PrefixForm(prefix=prefix_form, separator=separator, body=body_form)

    @property
    def needs_multi_line_encapsulation(self) -> bool:
        """[see superclass]"""
        return (
            self.prefix.needs_multi_line_encapsulation
            or self.body.needs_multi_line_encapsulation
        )

    needs_multi_line_encapsulation.__doc__ = (
        TextualForm.needs_multi_line_encapsulation.__doc__
    )

    def to_single_line(self) -> str:
        """[see superclass]"""

        return (
            self.prefix.to_single_line() + self.separator + self.body.to_single_line()
        )

    def to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:
        """[see superclass]"""

        prefix_lines: List[IndentedLine] = self.prefix.to_lines(
            config=config,
            indent=indent,
            leading_characters=leading_characters,
            trailing_characters=0,
        )

        separator = self.separator

        subform_lines = self.body.to_lines(
            config=config,
            indent=indent,
            leading_characters=(len(prefix_lines[-1]) if prefix_lines else 0)
            + len(separator),
            trailing_characters=trailing_characters,
        )

        if prefix_lines:
            subform_lines[0] = prefix_lines[-1] + separator + subform_lines[0].text
        else:
            subform_lines[0] = separator + subform_lines[0]

        return prefix_lines[:-1] + subform_lines

    to_multiple_lines.__doc__ = ComplexForm.to_multiple_lines.__doc__


class InfixForm(ComplexForm):
    """
    A hierarchical textual representation of a complex expression
    """

    PADDING_NONE = "none"
    PADDING_RIGHT = "right"
    PADDING_BOTH = "both"

    __PADDING_SPACES = {PADDING_NONE: 0, PADDING_RIGHT: 1, PADDING_BOTH: 2}

    def __init__(
        self,
        infix: str = "",
        infix_padding: str = PADDING_BOTH,
        subforms: Tuple[TextualForm, ...] = (),
    ) -> None:
        """
        :param infix: the infix operator separating the subforms
        :param infix_padding: the padding mode for the infix operator
        :param subforms: the subforms
        """

        if infix_padding is InfixForm.PADDING_RIGHT:
            subforms = tuple(
                subform.encapsulate(
                    condition=isinstance(subform, InfixForm), single_line=False
                )
                for subform in subforms
            )

        super().__init__(
            length=(
                sum(len(inner_representation) for inner_representation in subforms)
                + max(len(subforms) - 1, 0)
                * (len(infix) + (InfixForm.__PADDING_SPACES[infix_padding]))
            )
        )

        self.infix = infix
        self.infix_padding = infix_padding
        self.subforms = subforms

    @staticmethod
    def from_infix_expression(expression: InfixExpression) -> TextualForm:
        """
        Create a infix form from the given infix expression
        :param expression:
        :return:
        """

        subexpressions = expression.subexpressions_
        if len(subexpressions) == 1:
            return TextualForm.from_expression(subexpressions[0])

        subforms = tuple(
            TextualForm.from_expression(subexpression).encapsulate(
                condition=(
                    subexpression.precedence_ < expression.precedence_
                    if pos == 0
                    else subexpression.precedence_ <= expression.precedence_
                )
            )
            for pos, subexpression in enumerate(subexpressions)
        )

        infix = expression.infix_

        infix_padding = (
            InfixForm.PADDING_RIGHT
            if infix in [op.COMMA, op.COLON]
            else InfixForm.PADDING_NONE
            if infix in [op.DOT, op.SLICE, op.NONE]
            else InfixForm.PADDING_BOTH
        )

        return InfixForm(
            infix=infix.symbol, infix_padding=infix_padding, subforms=subforms
        )

    @property
    def needs_multi_line_encapsulation(self) -> bool:
        """[see superclass]"""
        return True

    needs_multi_line_encapsulation.__doc__ = (
        TextualForm.needs_multi_line_encapsulation.__doc__
    )

    def to_single_line(self) -> str:
        """[see superclass]"""

        if self.infix:
            infix_padding = self.infix_padding
            if infix_padding is InfixForm.PADDING_NONE:
                infix = self.infix
            elif infix_padding is InfixForm.PADDING_RIGHT:
                infix = f"{self.infix} "
            else:
                assert (
                    infix_padding is InfixForm.PADDING_BOTH
                ), "known infix padding mode"
                infix = f" {self.infix} "
        else:
            infix = ""

        return infix.join(subform.to_single_line() for subform in self.subforms)

    to_single_line.__doc__ = TextualForm.to_single_line.__doc__

    def to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:
        """[see superclass]"""

        subforms: Tuple[TextualForm, ...] = self.subforms

        result: List[IndentedLine] = []

        if len(subforms) == 1:

            result.extend(
                subforms[0].to_lines(
                    config=config,
                    indent=indent,
                    leading_characters=leading_characters,
                    trailing_characters=trailing_characters,
                )
            )

        else:

            last_idx = len(subforms) - 1
            infix = self.infix

            if self.infix_padding is InfixForm.PADDING_RIGHT:
                len_infix = len(infix)
                for idx, inner_representation in enumerate(subforms):
                    lines = inner_representation.to_lines(
                        config=config,
                        indent=indent,
                        leading_characters=(leading_characters if idx == 0 else 0),
                        trailing_characters=(
                            len_infix if idx < last_idx else trailing_characters
                        ),
                    )

                    if idx != last_idx:
                        # append infix to last line,
                        # except we're in the last representation
                        lines[-1] += infix

                    result.extend(lines)
            else:
                if self.infix_padding is InfixForm.PADDING_BOTH:
                    infix += " "

                len_infix = len(infix)
                for idx, inner_representation in enumerate(subforms):
                    lines = inner_representation.to_lines(
                        config=config,
                        indent=indent,
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
                        lines[0] = infix + lines[0]

                    result.extend(lines)

        return result

    to_multiple_lines.__doc__ = ComplexForm.to_multiple_lines.__doc__


#
# Public classes
#

__tracker = AllTracker(globals())


class PythonExpressionFormatter(ExpressionFormatter):
    """
    Formats expression objects as Python expressions, in line with the `black` style
    """

    def __init__(
        self, max_width: int = 80, indent_width: int = 4, single_line: bool = False
    ):
        """
        :param max_width: the maximum line width (ignored when enforcing single-line \
            text (default: 80)
        :param indent_width: the width of one indentation in spaces (default: 4)
        :param single_line: if `False`, include line breaks to keep the width within \
            maximum bounds (default: `False`)
        """
        self.config = FormattingConfig(
            max_width=max_width, indent_width=indent_width, single_line=single_line
        )

    def to_text(self, expression: Expression) -> str:
        """[see superclass]"""

        form = TextualForm.from_expression(expression)

        # if the outermost form needs multiline encapsulation, do it
        form = form.encapsulate(
            condition=form.needs_multi_line_encapsulation, single_line=False
        )

        return form.to_text(self.config)

    to_text.__doc__ = ExpressionFormatter.to_text.__doc__


# Register class PythonExpressionFormat as the default display form
_DEFAULT_PYTHON_EXPRESSION_FORMATTER = PythonExpressionFormatter()
# noinspection PyProtectedMember
ExpressionFormatter._register_default_format(_DEFAULT_PYTHON_EXPRESSION_FORMATTER)

__tracker.validate()
