# coding=utf-8
"""Base classes with wrappers around sklearn transformers."""

import logging
from abc import ABC, abstractmethod
from types import new_class
from typing import *

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from yieldengine import Sample
from yieldengine.df import DataFrameEstimator

log = logging.getLogger(__name__)

_BaseTransformer = TypeVar(
    "_BaseTransformer", bound=Union[BaseEstimator, TransformerMixin]
)


class DataFrameTransformer(DataFrameEstimator[_BaseTransformer], TransformerMixin, ABC):
    """Wrap around an sklearn transformer and return dataframes.

    Implementations must define `_make_base_transformer` and `_get_columns_original`.

    :param: base_transformer the sklearn transformer to be wrapped
    """

    F_COLUMN_ORIGINAL = "column_original"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._columns_out = None
        self._columns_original = None

    @property
    def base_transformer(self) -> _BaseTransformer:
        """The base sklearn transformer"""
        return self.base_estimator

    # noinspection PyPep8Naming
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Call the transform method of the base transformer ``self.base_transformer``.

        :param X: dataframe to transform
        :return: transformed dataframe
        """
        self._check_parameter_types(X, None)

        transformed = self._base_transform(X)

        return self._transformed_to_df(
            transformed=transformed, index=X.index, columns=self.columns_out
        )

    # noinspection PyPep8Naming
    def fit_transform(
        self, X: pd.DataFrame, y: Optional[pd.Series] = None, **fit_params
    ) -> pd.DataFrame:
        """Call the fit_transform method of the base transformer
        `self.base_transformer`.

        :param X: dataframe to transform
        :param y: series of training targets
        :param fit_params: parameters passed to the fit method of the base transformer
        :return: dataframe of transformed sample
        """
        self._check_parameter_types(X, y)

        transformed = self._base_fit_transform(X, y, **fit_params)

        self._post_fit(X, y, **fit_params)

        return self._transformed_to_df(
            transformed=transformed, index=X.index, columns=self.columns_out
        )

    # noinspection PyPep8Naming
    def inverse_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Apply inverse transformations in reverse order on the base transformer.

        All estimators in the pipeline must support ``inverse_transform``.
        :param X: dataframe of samples
        :return: dataframe of inversed samples
        """

        self._check_parameter_types(X, None)

        transformed = self._base_inverse_transform(X)

        return self._transformed_to_df(
            transformed=transformed, index=X.index, columns=self.columns_in
        )

    def fit_transform_sample(self, sample: Sample) -> Sample:
        """
        Fit and transform with input and output being a :class:`~yieldengine.Sample`
        object.
        :param sample: `Sample` object used as input
        :return: transformed `Sample` object
        """
        return Sample(
            observations=pd.concat(
                objs=[self.fit_transform(sample.features), sample.target], axis=1
            ),
            target_name=sample.target_name,
        )

    @property
    def columns_original(self) -> pd.Series:
        """Series mapping output column names to the original columns names.

        Series with index the name of the output columns and with values the
        original name of the column."""
        self._ensure_fitted()
        if self._columns_original is None:
            self._columns_original = (
                self._get_columns_original()
                .rename(self.F_COLUMN_ORIGINAL)
                .rename_axis(index=self.F_COLUMN)
            )
        return self._columns_original

    @property
    def columns_out(self) -> pd.Index:
        """The `pd.Index` of names of the output columns."""
        return self.columns_original.index

    @classmethod
    def _make_base_estimator(cls, **kwargs) -> _BaseTransformer:
        return cls._make_base_transformer(**kwargs)

    @classmethod
    @abstractmethod
    def _make_base_transformer(cls, **kwargs) -> _BaseTransformer:
        pass

    @abstractmethod
    def _get_columns_original(self) -> pd.Series:
        """Return the series mapping output column names to original columns names."""
        pass

    # noinspection PyPep8Naming,PyUnusedLocal
    def _post_fit(
        self, X: pd.DataFrame, y: Optional[pd.Series] = None, **fit_params
    ) -> None:
        super()._post_fit(X=X, y=y, **fit_params)
        self._columns_out = None
        self._columns_original = None

    @staticmethod
    def _transformed_to_df(
        transformed: Union[pd.DataFrame, np.ndarray], index: pd.Index, columns: pd.Index
    ):
        if isinstance(transformed, pd.DataFrame):
            return transformed
        else:
            return pd.DataFrame(data=transformed, index=index, columns=columns)

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


class NDArrayTransformerDF(
    DataFrameTransformer[_BaseTransformer], Generic[_BaseTransformer], ABC
):
    """`DataFrameTransformer` whose base transformer only accepts numpy ndarrays."""

    # noinspection PyPep8Naming
    def _base_fit(
        self, X: pd.DataFrame, y: Optional[pd.Series], **fit_params
    ) -> _BaseTransformer:
        # noinspection PyUnresolvedReferences
        return self.base_transformer.fit(X.values, y.values, **fit_params)

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
    DataFrameTransformer[_BaseTransformer], Generic[_BaseTransformer], ABC
):
    """Abstract base class for a `DataFrameTransformer`.

    All output columns of a ColumnPreservingTransformer have the same names as their
    associated input columns. Some columns can be removed.
    Implementations must define `_make_base_transformer` and `_get_columns_out`.
    """

    @abstractmethod
    def _get_columns_out(self) -> pd.Index:
        """Column labels for arrays returned by the fitted transformer."""
        pass

    def _get_columns_original(self) -> pd.Series:
        columns_out = self._get_columns_out()
        return pd.Series(index=columns_out, data=columns_out.values)


class ConstantColumnTransformer(
    ColumnPreservingTransformer[_BaseTransformer], Generic[_BaseTransformer], ABC
):
    """Abstract base class for a `DataFrameTransformer`.

    A ConstantColumnTransformer does not add, remove, or rename any of the input
    columns. Implementations must define `_make_base_transformer`.
    """

    def _get_columns_out(self) -> pd.Index:
        return self.columns_in


def df_transformer(
    cls: Type[_BaseTransformer] = None,
    *,
    df_transformer_type: Type[
        DataFrameTransformer[_BaseTransformer]
    ] = ConstantColumnTransformer,
) -> Union[
    Callable[[Type[_BaseTransformer]], Type[DataFrameTransformer[_BaseTransformer]]],
    Type[DataFrameTransformer[_BaseTransformer]],
]:
    """Class decorator wrapping an sklearn transformer in a `DataFrameTransformer`.

    :param cls: the transformer class to wrap
    :param df_transformer_type: optional parameter indicating the \
                                `DataFrameTransformer` class to be used for wrapping; \
                                defaults to `ConstantColumnTransformer`
    :return: the resulting `DataFrameTransformer` with `cls` as the base \
             transformer
    """

    def _init_class_namespace(namespace: Dict[str, Any]) -> None:
        # noinspection PyProtectedMember
        namespace[
            df_transformer_type._make_base_transformer.__name__
        ] = lambda **kwargs: cls(**kwargs)

    def _decorate(
        _cls: Type[_BaseTransformer]
    ) -> Type[DataFrameTransformer[_BaseTransformer]]:
        return cast(
            Type[DataFrameTransformer[_BaseTransformer]],
            new_class(
                name=_cls.__name__,
                bases=(df_transformer_type,),
                exec_body=_init_class_namespace,
            ),
        )

    if not issubclass(df_transformer_type, DataFrameTransformer):
        raise ValueError(
            f"arg df_transformer_type not a "
            f"{DataFrameTransformer.__name__} class: {df_transformer_type}"
        )
    if cls is None:
        return _decorate
    else:
        return _decorate(cls)
