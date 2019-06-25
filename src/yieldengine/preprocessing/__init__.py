import logging
from typing import *

import pandas as pd
from sklearn.preprocessing import (
    FunctionTransformer,
    MaxAbsScaler,
    MinMaxScaler,
    Normalizer,
    PowerTransformer,
    QuantileTransformer,
    RobustScaler,
    StandardScaler,
)

from yieldengine.df.transform import (
    ColumnPreservingTransformer,
    make_constant_column_transformer_class,
)

log = logging.getLogger(__name__)


MaxAbsScalerDF = make_constant_column_transformer_class(source_transformer=MaxAbsScaler)

MinMaxScalerDF = make_constant_column_transformer_class(source_transformer=MinMaxScaler)

NormalizerDF = make_constant_column_transformer_class(source_transformer=Normalizer)

PowerTransformerDF = make_constant_column_transformer_class(
    source_transformer=PowerTransformer
)

QuantileTransformerDF = make_constant_column_transformer_class(
    source_transformer=QuantileTransformer
)

RobustScalerDF = make_constant_column_transformer_class(source_transformer=RobustScaler)

StandardScalerDF = make_constant_column_transformer_class(
    source_transformer=StandardScaler
)


class FunctionTransformerDF(ColumnPreservingTransformer[FunctionTransformer]):
    def _get_columns_out(self) -> pd.Index:
        if isinstance(self._columns_out_provided, Callable):
            return self._columns_out_provided()
        else:
            # ignore error, type is already checked correctly in constructor:
            # noinspection PyTypeChecker
            return self._columns_out_provided

    def __init__(
        self, columns_out: Union[pd.Index, Callable[[None], pd.Index]], **kwargs
    ) -> None:

        if columns_out is None:
            raise ValueError("'columns_out' is required")

        if not isinstance(columns_out, pd.Index) and not isinstance(
            columns_out, Callable
        ):
            raise TypeError(
                "'columns_out' must be pandas.Index or callable->pandas.Index"
            )

        self._columns_out_provided = columns_out

        super().__init__(**kwargs)

    @classmethod
    def _make_base_transformer(cls, **kwargs) -> FunctionTransformer:
        return FunctionTransformer(**kwargs)
