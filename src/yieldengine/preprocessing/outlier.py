import logging
from typing import Optional

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from yieldengine.df.transform import df_transformer

log = logging.getLogger(__name__)


@df_transformer
class OutlierRemoverDF(BaseEstimator, TransformerMixin):
    """
    Remove outliers according to Tukey's method, respective to a multiple of the \
    inter-quartile range (IQR)
    """

    def __init__(self, iqr_multiple: float):
        if iqr_multiple < 0.0:
            raise ValueError(f"arg iqr_multiple is negative: {iqr_multiple}")
        self.iqr_multiple = iqr_multiple
        self.threshold_low_ = None
        self.threshold_high_ = None

    # noinspection PyPep8Naming
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "OutlierRemoverDF":
        q1: pd.Series = X.quantile(q=0.25)
        q3: pd.Series = X.quantile(q=0.75)
        threshold_iqr: pd.Series = (q3 - q1) * self.iqr_multiple
        self.threshold_low_ = q1 - threshold_iqr
        self.threshold_high_ = q3 + threshold_iqr

    # noinspection PyPep8Naming
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.where(cond=(X >= self.threshold_low_) & (X <= self.threshold_high_))
