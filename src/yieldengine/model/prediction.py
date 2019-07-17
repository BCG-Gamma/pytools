# coding=utf-8
"""Fitted models with cross-validation.

The `~ModelFitCV` encapsulates a fully trained model. It contains a `Model` (
preprocessing + estimator), a dataset given by a `Sample` object and a
cross-validation method. The model is fitted accordingly.
"""
import copy
import logging
from typing import *

import numpy as np
import pandas as pd
from joblib import delayed, Parallel
from sklearn.model_selection import BaseCrossValidator

from yieldengine import Sample
from yieldengine.model import Model

log = logging.getLogger(__name__)


class ModelFitCV:
    """Full information about a fitted model with cross-validation.

    :param Model model: model to be fitted
    :param BaseCrossValidator cv: the cross validator generating the train splits
    :param Sample sample: the sample from which the training sets are drawn
    """

    __slots__ = [
        "_model",
        "_cv",
        "_sample",
        "_predictions_for_all_samples",
        "_model_by_split",
        "_n_jobs",
        "_shared_memory",
        "_verbose",
    ]

    F_SPLIT_ID = "split_id"
    F_PREDICTION = "prediction"
    F_TARGET = "target"

    def __init__(
        self,
        model: Model,
        cv: BaseCrossValidator,
        sample: Sample,
        n_jobs: int = 1,
        shared_memory: bool = True,
        verbose: int = 0,
    ) -> None:
        self._model = model
        self._cv = cv
        self._sample = sample
        self._model_by_split: Optional[List[Model]] = None
        self._predictions_for_all_samples: Optional[pd.DataFrame] = None
        self._n_jobs = n_jobs
        self._shared_memory = shared_memory
        self._verbose = verbose

    @property
    def model(self) -> Model:
        """The ingoing, usually unfitted model to be fitted to the training splits."""
        return self._model

    @property
    def cv(self) -> BaseCrossValidator:
        """The cross validator generating the train splits.
        """
        return self._cv

    @property
    def sample(self) -> Sample:
        """The sample from which the training sets are drawn
        """
        return self._sample

    @property
    def n_splits(self) -> int:
        """Number of splits in this model fit."""
        return self.cv.get_n_splits(X=self.sample.features, y=self.sample.target)

    def fitted_models(self) -> Iterator[Model]:
        """Iterator of all models fitted for the train splits."""
        self._fit()
        return iter(self._model_by_split)

    def fitted_model(self, split_id: int) -> Model:
        """Return the fitted model for a given split.

        :param split_id: start index of test split
        :return: the model fitted for the train split at the given index
        """
        self._fit()
        return self._model_by_split[split_id]

    def _fit(self) -> None:

        if self._model_by_split is not None:
            return

        model = self.model
        sample = self.sample

        self._model_by_split: List[Model] = self._parrallel()(
            delayed(self._fit_model_for_split)(
                model.clone(),
                sample.select_observations_by_position(positions=train_indices),
            )
            for train_indices, _ in self.cv.split(sample.features, sample.target)
        )

    def _parrallel(self) -> Parallel:
        return Parallel(
            n_jobs=self._n_jobs,
            require="sharedmem" if self._shared_memory else None,
            verbose=self._verbose,
        )

    def _series_for_split(self, split_id: int, column: str) -> pd.Series:
        all_predictions: pd.DataFrame = self.predictions_for_all_splits()
        return all_predictions.xs(key=split_id, level=ModelFitCV.F_SPLIT_ID).loc[
            :, column
        ]

    def predictions_for_split(self, split_id: int) -> pd.Series:
        """The predictions for a given split.

        :return: the series of predictions of the split
        """
        return self._series_for_split(split_id=split_id, column=ModelFitCV.F_PREDICTION)

    def targets_for_split(self, split_id: int) -> pd.Series:
        """Return the target for this split.

        :return: the series of targets for this split"""
        return self._series_for_split(split_id=split_id, column=ModelFitCV.F_TARGET)

    def predictions_for_all_splits(self) -> pd.DataFrame:
        """For each split of this Predictor's CV, predict all values in the test set.

        The result is a data frame with one row per prediction, indexed by the
        observations in the sample and the split id (index level F_SPLIT_ID),
        and with columns F_PREDICTION (the predicted value for the
        given observation and split), and F_TARGET (the actual target)

        Note that there can be multiple prediction rows per observation if the test
        splits overlap.

        :return: the data frame with the predictions per observation and test split
        """

        if self._predictions_for_all_samples is None:

            self._fit()

            sample = self.sample

            def _predictions_for_split(
                split_id: int, test_indices: np.ndarray
            ) -> pd.DataFrame:
                test_sample = sample.select_observations_by_position(
                    positions=test_indices
                )
                return pd.DataFrame(
                    data={
                        ModelFitCV.F_SPLIT_ID: split_id,
                        ModelFitCV.F_PREDICTION: self.fitted_model(
                            split_id=split_id
                        ).pipeline.predict(X=test_sample.features),
                    },
                    index=test_sample.index,
                )

            predictions_per_split: Iterable[pd.DataFrame] = [
                _predictions_for_split(split_id=split_id, test_indices=test_indices)
                for split_id, (_, test_indices) in enumerate(
                    self.cv.split(sample.features, sample.target)
                )
            ]

            self._predictions_for_all_samples = (
                pd.concat(predictions_per_split)
                .join(sample.target.rename(ModelFitCV.F_TARGET))
                .set_index(ModelFitCV.F_SPLIT_ID, append=True)
            )

        return self._predictions_for_all_samples

    def copy_with_sample(self, sample: Sample):
        """Copy the predictor with some new `Sample`.

        :param sample: the `Sample` used for the copy
        :return: the copy of self
        """
        copied_predictor = copy.copy(self)
        copied_predictor._sample = sample
        copied_predictor._predictions_for_all_samples = None
        return copied_predictor

    @staticmethod
    def _fit_model_for_split(model: Model, train_sample: Sample) -> Model:
        """Fit a model using a sample.

        :param model:  the `Model` to fit
        :param train_sample: `Sample` to fit on
        :return: tuple of the the split_id and the fitted `Model`
        """
        model.pipeline.fit(X=train_sample.features, y=train_sample.target)
        return model
