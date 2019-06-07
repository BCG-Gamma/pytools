from typing import *

import numpy as np
import pandas as pd

from yieldengine.model.prediction import PredictorCV


class UnivariateSimulation:
    __slots__ = ["_predictor"]

    F_FOLD_ID = "fold_id"
    F_PARAMETER_VALUE = "parameter_value"
    F_RELATIVE_YIELD_CHANGE = "relative_yield_change"

    def __init__(self, predictor: PredictorCV):
        self._predictor = predictor

    @property
    def predictor(self) -> PredictorCV:
        return self._predictor

    def simulate_yield_change(
        self, parameterized_feature: str, parameter_values: np.ndarray
    ) -> pd.DataFrame:
        if parameterized_feature not in self.predictor.sample.feature_names:
            raise ValueError(f"Feature '{parameterized_feature}' not in sample")

        results = []

        for fold_id, (train_indices, test_indices) in enumerate(
            self.predictor.cv.split(
                self.predictor.sample.features, self.predictor.sample.target
            )
        ):
            for parameter_value in parameter_values:
                pipeline = self.predictor.pipeline(fold_id)
                predictions_for_fold: np.ndarray = self.predictor.predictions_for_fold(
                    fold_id=fold_id
                )

                test_data_features = self.predictor.sample.select_observations(
                    numbers=test_indices
                ).features.copy()

                test_data_features.loc[:, parameterized_feature] = parameter_value

                predictions_simulated: np.ndarray = pipeline.predict(
                    X=test_data_features
                )

                relative_yield_change = (
                    predictions_simulated.mean(axis=0)
                    / predictions_for_fold.mean(axis=0)
                ) - 1

                results.append(
                    {
                        UnivariateSimulation.F_FOLD_ID: fold_id,
                        UnivariateSimulation.F_PARAMETER_VALUE: parameter_value,
                        UnivariateSimulation.F_RELATIVE_YIELD_CHANGE: relative_yield_change,
                    }
                )

        return pd.DataFrame(results)

    @staticmethod
    def aggregate_simulated_yield_change(
        foldwise_results: pd.DataFrame, percentiles: List[int]
    ):
        def percentile(n: int):
            def percentile_(x: float):
                return np.percentile(x, n)

            percentile_.__name__ = "percentile_%s" % n
            return percentile_

        return (
            foldwise_results.drop(columns=UnivariateSimulation.F_FOLD_ID)
            .groupby(by=UnivariateSimulation.F_PARAMETER_VALUE)
            .agg([percentile(p) for p in percentiles])
        )
