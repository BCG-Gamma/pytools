# coding=utf-8

import logging
from abc import ABC, ABCMeta, abstractmethod
from typing import *

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

log = logging.getLogger(__name__)

_BaseTransformer = TypeVar(
    "_BaseTransformer", bound=Union[BaseEstimator, TransformerMixin]
)


class DataFrameTransformer(
    ABC, BaseEstimator, TransformerMixin, Generic[_BaseTransformer]
):
    """
    Wraps around an sklearn transformer and ensures that the X and y objects passed
    and returned are pandas data frames with valid column names

    :param base_transformer the sklearn transformer to be wrapped
    """

    F_COLUMN = "column"
    F_COLUMN_ORIGINAL = "column_original"

    def __init__(self, **kwargs) -> None:
        super(BaseEstimator).__init__()
        super(TransformerMixin).__init__()
        self._base_transformer = type(self)._make_base_transformer(**kwargs)
        self._columns_in = None
        self._columns_out = None
        self._columns_original = None

    @classmethod
    @abstractmethod
    def _make_base_transformer(cls, **kwargs) -> _BaseTransformer:
        pass

    @property
    def base_transformer(self) -> _BaseTransformer:
        return self._base_transformer

    def is_fitted(self) -> bool:
        return self._columns_in is not None

    @property
    def columns_in(self) -> pd.Index:
        self._ensure_fitted()
        return self._columns_in

    @property
    def columns_out(self) -> pd.Index:
        return self.columns_original.index

    @property
    def columns_original(self) -> pd.Series:
        self._ensure_fitted()
        if self._columns_original is None:
            self._columns_original = (
                self._get_columns_original()
                .rename(DataFrameTransformer.F_COLUMN_ORIGINAL)
                .rename_axis(index=DataFrameTransformer.F_COLUMN)
            )
        return self._columns_original

    def _ensure_fitted(self):
        if not self.is_fitted():
            raise RuntimeError("transformer not fitted")

    @abstractmethod
    def _get_columns_original(self) -> pd.Series:
        """
        :return: a mapping from this transformer's output columns to the original
        columns as a series
        """
        pass

    def get_params(self, deep=True) -> Dict[str, Any]:
        """
        Get parameters for this estimator.

        :param deep If True, will return the parameters for this estimator and
        contained subobjects that are estimators

        :returns params Parameter names mapped to their values
        """
        # noinspection PyUnresolvedReferences
        return self.base_transformer.get_params(deep=deep)

    def set_params(self, **kwargs) -> "DataFrameTransformer":
        """
        Set the parameters of this estimator.

        Valid parameter keys can be listed with ``get_params()``.

        :returns self
        """
        # noinspection PyUnresolvedReferences
        self.base_transformer.set_params(**kwargs)
        return self

    # noinspection PyPep8Naming,PyUnusedLocal
    def _post_fit(
        self, X: pd.DataFrame, y: Optional[pd.Series] = None, **fit_params
    ) -> None:
        self._columns_in = X.columns.rename(DataFrameTransformer.F_COLUMN)
        self._columns_out = None
        self._columns_original = None

    def _transformed_to_df(
        self,
        transformed: Union[pd.DataFrame, np.ndarray],
        index: pd.Index,
        columns: pd.Index,
    ):
        if isinstance(transformed, pd.DataFrame):
            return transformed
        else:
            return pd.DataFrame(data=transformed, index=index, columns=columns)

    # noinspection PyPep8Naming
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None, **fit_params) -> None:
        self._check_parameter_types(X, y)

        self._base_fit(X, y, **fit_params)

        self._post_fit(X, y, **fit_params)

    # noinspection PyPep8Naming
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        self._check_parameter_types(X, None)

        transformed = self._base_transform(X)

        return self._transformed_to_df(
            transformed=transformed, index=X.index, columns=self.columns_out
        )

    # noinspection PyPep8Naming
    def fit_transform(
        self, X: pd.DataFrame, y: Optional[pd.Series] = None, **fit_params
    ) -> pd.DataFrame:
        self._check_parameter_types(X, y)

        transformed = self._base_fit_transform(X, y, **fit_params)

        self._post_fit(X, y, **fit_params)

        return self._transformed_to_df(
            transformed=transformed, index=X.index, columns=self.columns_out
        )

    # noinspection PyPep8Naming
    def inverse_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        self._check_parameter_types(X, None)

        transformed = self._base_inverse_transform(X)

        return self._transformed_to_df(
            transformed=transformed, index=X.index, columns=self.columns_in
        )

    def fit_transform_sample(self, sample: Sample) -> Sample:
        return Sample(
            observations=pd.concat(
                objs=[self.fit_transform(sample.features), sample.target], axis=1
            ),
            target_name=sample.target_name,
        )

    # noinspection PyPep8Naming
    def _base_fit(self, X: pd.DataFrame, y: Optional[pd.Series], **fit_params):
        # noinspection PyUnresolvedReferences
        self.base_transformer.fit(X, y, **fit_params)

    # noinspection PyPep8Naming
    def _base_transform(self, X: pd.DataFrame) -> np.ndarray:
        # noinspection PyUnresolvedReferences
        return self.base_transformer.transform(X)

    # noinspection PyPep8Naming
    def _base_fit_transform(
        self, X: pd.DataFrame, y: Optional[pd.Series], **fit_params
    ) -> np.ndarray:
        return self.base_transformer.fit_transform(X, y, **fit_params)

    # noinspection PyPep8Naming
    def _base_inverse_transform(self, X: pd.DataFrame) -> np.ndarray:
        # noinspection PyUnresolvedReferences
        return self.base_transformer.inverse_transform(X)

    # noinspection PyPep8Naming
    @staticmethod
    def _check_parameter_types(X: pd.DataFrame, y: Optional[pd.Series]) -> None:
        if not isinstance(X, pd.DataFrame):
            raise TypeError("arg X must be a DataFrame")
        if y is not None and not isinstance(y, pd.Series):
            raise TypeError("arg y must be a Series")


class NumpyOnlyTransformer(
    DataFrameTransformer[_BaseTransformer], Generic[_BaseTransformer], metaclass=ABCMeta
):
    """
    Special case of DataFrameTransformer where the base transformer does not accept
    data frames, but only numpy ndarrays
    """

    # noinspection PyPep8Naming
    def _base_fit(self, X: pd.DataFrame, y: Optional[pd.Series], **fit_params):
        # noinspection PyUnresolvedReferences
        self.base_transformer.fit(X.values, y.values, **fit_params)

    # noinspection PyPep8Naming
    def _base_transform(self, X: pd.DataFrame) -> np.ndarray:
        # noinspection PyUnresolvedReferences
        return self.base_transformer.transform(X.values)

    # noinspection PyPep8Naming
    def _base_fit_transform(
        self, X: pd.DataFrame, y: Optional[pd.Series], **fit_params
    ) -> np.ndarray:
        return self.base_transformer.fit_transform(X.values, y.values, **fit_params)

    # noinspection PyPep8Naming
    def _base_inverse_transform(self, X: pd.DataFrame) -> np.ndarray:
        # noinspection PyUnresolvedReferences
        return self.base_transformer.inverse_transform(X.values)


class ColumnPreservingTransformer(
    DataFrameTransformer[_BaseTransformer], Generic[_BaseTransformer], metaclass=ABCMeta
):
    """
    All output columns of a ColumnPreservingTransformer have the same names as their associated input columns
    """

    @abstractmethod
    def _get_columns_out(self) -> pd.Index:
        """
        :returns column labels for arrays returned by the fitted transformer
        """
        pass

    def _get_columns_original(self) -> pd.Series:
        columns_out = self._get_columns_out()
        return pd.Series(index=columns_out, data=columns_out.values)


class ConstantColumnTransformer(
    ColumnPreservingTransformer[_BaseTransformer],
    Generic[_BaseTransformer],
    metaclass=ABCMeta,
):
    """
    A ConstantColumnTransformer does not add, remove, or rename any of the input columns
    """

    def _get_columns_out(self) -> pd.Index:
        return self.columns_in
