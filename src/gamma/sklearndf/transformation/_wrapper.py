"""
Specialised transformer wrappers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Generic, Optional

import numpy as np
import pandas as pd

from gamma.sklearndf import T_Transformer
from gamma.sklearndf._wrapper import TransformerWrapperDF

log = logging.getLogger(__name__)


class NDArrayTransformerWrapperDF(
    TransformerWrapperDF[T_Transformer], Generic[T_Transformer], ABC
):
    """
    `TransformerDF` whose delegate transformer only accepts numpy ndarrays.

    Wraps around the delegate transformer and converts the data frame to an array when
    needed.
    """

    # noinspection PyPep8Naming
    def _fit(
        self, X: pd.DataFrame, y: Optional[pd.Series], **fit_params
    ) -> T_Transformer:
        # noinspection PyUnresolvedReferences
        return self.delegate_estimator.fit(X.values, y.values, **fit_params)

    # noinspection PyPep8Naming
    def _transform(self, X: pd.DataFrame) -> np.ndarray:
        # noinspection PyUnresolvedReferences
        return self.delegate_estimator.transform(X.values)

    # noinspection PyPep8Naming
    def _fit_transform(
        self, X: pd.DataFrame, y: Optional[pd.Series], **fit_params
    ) -> np.ndarray:
        return self.delegate_estimator.fit_transform(X.values, y.values, **fit_params)

    # noinspection PyPep8Naming
    def _inverse_transform(self, X: pd.DataFrame) -> np.ndarray:
        # noinspection PyUnresolvedReferences
        return self.delegate_estimator.inverse_transform(X.values)


class ColumnSubsetTransformerWrapperDF(
    TransformerWrapperDF[T_Transformer], Generic[T_Transformer], ABC
):
    """
    Transforms a data frame without changing column names, but possibly removing
    columns.

    All output columns of a :class:`ColumnSubsetTransformerWrapperDF` have the same
    names as their associated input columns. Some columns can be removed.
    Implementations must define ``_make_delegate_estimator`` and ``_get_columns_out``.
    """

    @abstractmethod
    def _get_columns_out(self) -> pd.Index:
        # return column labels for arrays returned by the fitted transformer.
        pass

    def _get_columns_original(self) -> pd.Series:
        # return the series with output columns in index and output columns as values
        columns_out = self._get_columns_out()
        return pd.Series(index=columns_out, data=columns_out.values)


class ColumnPreservingTransformerWrapperDF(
    ColumnSubsetTransformerWrapperDF[T_Transformer], Generic[T_Transformer], ABC
):
    """
    Transform a data frame keeping exactly the same columns.

    A ``ColumnPreservingTransformerWrapperDF`` does not add, remove, or rename any of
    the input columns.
    """

    def _get_columns_out(self) -> pd.Index:
        return self.columns_in


class BaseDimensionalityReductionWrapperDF(
    TransformerWrapperDF[T_Transformer], Generic[T_Transformer], ABC
):
    """
    Transform data making dimensionality redcution style transform.
    """

    @abstractmethod
    def _get_columns_out(self) -> pd.Index:
        # return column labels for arrays returned by the fitted transformer.
        pass

    def _get_columns_original(self) -> pd.Series:
        raise AttributeError(
            "columns_original is not defined for dimensionality reduction transformers"
        )


class AnonymousDimensionalityReductionWrapperDF(
    BaseDimensionalityReductionWrapperDF[T_Transformer], Generic[T_Transformer], ABC
):
    def _get_columns_out(self) -> pd.Index:
        # todo: implement this
        pass


COMPONENTS = "components_"


class NamedDimensionalityReductionWrapperDF(
    BaseDimensionalityReductionWrapperDF[T_Transformer], Generic[T_Transformer], ABC
):
    """
    Apply dimensionality reduction on a dataframe.

    The delegate transformer has a ``componnents_`` attribute of the form (
    n_components, n_features).
    """

    def _get_columns_out(self) -> pd.Index:
        if not hasattr(self.delegate_estimator, COMPONENTS):
            raise AttributeError(
                f"NamedDimensionalityReductionWrapperDF should have "
                f"a {COMPONENTS} attribute but does not have. The "
                f"delegate "
                f"estimator is {repr(T_Transformer)}"
            )
        feature_format = "x_{}"
        n_features = getattr(self.delegate_estimator, COMPONENTS).shape[0]
        return pd.Index([feature_format.format(i) for i in range(n_features)])


GET_SUPPORT = "get_support"


class FeatureSelectionWrapperDF(
    ColumnSubsetTransformerWrapperDF[T_Transformer], Generic[T_Transformer], ABC
):
    def _get_columns_out(self) -> pd.Index:
        if not (
            hasattr(self.delegate_estimator, GET_SUPPORT)
            and callable(getattr(self.delegate_estimator, GET_SUPPORT))
        ):
            raise AttributeError(
                f"FeatureSelectionWrapperDF should have a "
                f"{GET_SUPPORT} method but does not have. The "
                f"delegate "
                f"estimator is {repr(T_Transformer)}"
            )
        support_indices = getattr(self.delegate_estimator, GET_SUPPORT)(indices=True)
        return self.columns_in[support_indices]
