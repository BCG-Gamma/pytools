import warnings
from typing import *

import numpy as np
import pandas as pd
import pytest
from sklearn import datasets
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import AdaBoostRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import make_scorer, mean_squared_error
from sklearn.preprocessing import OneHotEncoder
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeRegressor, ExtraTreeRegressor

# noinspection PyUnresolvedReferences
from tests.shared_fixtures import batch_table
from yieldengine.loading.sample import Sample
from yieldengine.modeling.selection import (
    BEST_MODEL_RANK,
    Model,
    ModelRanker,
    ModelRanking,
    ModelZoo,
    RankedModel,
)
from yieldengine.modeling.validation import CircularCrossValidator
import logging

log = logging.getLogger(__name__)


@pytest.fixture
def model_zoo(LGBMRegressor) -> ModelZoo:
    return ModelZoo(
        [
            Model(
                estimator=LGBMRegressor(),
                parameter_grid={
                    "max_depth": (5, 10),
                    "min_split_gain": (0.1, 0.2),
                    "num_leaves": (50, 100, 200),
                },
            ),
            Model(
                estimator=AdaBoostRegressor(), parameter_grid={"n_estimators": (50, 80)}
            ),
            Model(
                estimator=RandomForestRegressor(),
                parameter_grid={"n_estimators": (50, 80)},
            ),
            Model(
                estimator=DecisionTreeRegressor(),
                parameter_grid={"max_depth": (0.5, 1.0), "max_features": (0.5, 1.0)},
            ),
            Model(
                estimator=ExtraTreeRegressor(),
                parameter_grid={"max_depth": (5, 10, 12)},
            ),
            Model(estimator=SVR(), parameter_grid={"gamma": (0.5, 1), "C": (50, 100)}),
            Model(
                estimator=LinearRegression(),
                parameter_grid={"normalize": (False, True)},
            ),
        ]
    )


@pytest.fixture
def sample(batch_table: pd.DataFrame) -> Sample:
    # drop columns that should not take part in modeling
    batch_table = batch_table.drop(columns=["Date", "Batch Id"])

    # replace values of +/- infinite with n/a, then drop all n/a columns:
    batch_table = batch_table.replace([np.inf, -np.inf], np.nan).dropna(
        axis=1, how="all"
    )

    sample = Sample(observations=batch_table, target_name="Yield")
    return sample


@pytest.fixture
def preprocessing_step(sample: Sample) -> Tuple[str, BaseEstimator]:
    # define a ColumnTransformer to pre-process:
    preprocessor = ColumnTransformer(
        [
            (
                "numerical",
                SimpleImputer(strategy="mean"),
                sample.features_by_type(dtype=sample.DTYPE_NUMERICAL),
            ),
            (
                "categorical",
                OneHotEncoder(sparse=False, handle_unknown="ignore"),
                sample.features_by_type(dtype=sample.DTYPE_OBJECT),
            ),
        ]
    )

    # define a sklearn Pipeline step, containing the preprocessor defined above:
    return "prep", preprocessor


def test_model_ranker(
    batch_table: pd.DataFrame, model_zoo: ModelZoo, sample: Sample, preprocessing_step
) -> None:

    # define the circular cross validator with just 5 folds (to speed up testing)
    circular_cv = CircularCrossValidator(test_ratio=0.20, num_folds=5)

    model_ranker: ModelRanker = ModelRanker(
        zoo=model_zoo,
        preprocessing_step=preprocessing_step,
        cv=circular_cv,
        scoring=make_scorer(mean_squared_error, greater_is_better=False),
    )

    # run the ModelRanker to retrieve a ranking
    model_ranking: ModelRanking = model_ranker.run(sample=sample)

    assert len(model_ranking) > 0
    assert isinstance(model_ranking.model(rank=BEST_MODEL_RANK), RankedModel)
    assert (
        model_ranking.model(rank=0).score
        >= model_ranking.model(rank=1).score
        >= model_ranking.model(rank=2).score
        >= model_ranking.model(rank=3).score
        >= model_ranking.model(rank=4).score
        >= model_ranking.model(rank=len(model_ranking) - 1).score
    )

    # check if parameters set for estimators actually match expected:
    for r in range(0, len(model_ranking)):
        m: RankedModel = model_ranking.model(r)
        assert set(m.parameters).issubset(m.estimator.get_params())

    log.info(f"\n{model_ranking}")


def test_model_ranker_refit(
    batch_table: pd.DataFrame, sample: Sample, preprocessing_step
) -> None:

    # to test refit, we use only linear regression, to simply check "coef"
    model_zoo = ModelZoo(
        [
            Model(
                estimator=LinearRegression(),
                parameter_grid={"normalize": (False, True)},
            )
        ]
    )

    # define the circular cross validator with just 5 folds (to speed up testing)
    circular_cv = CircularCrossValidator(test_ratio=0.20, num_folds=5)

    # define a model ranker
    model_ranker: ModelRanker = ModelRanker(
        zoo=model_zoo,
        preprocessing_step=preprocessing_step,
        cv=circular_cv,
        scoring=make_scorer(mean_squared_error, greater_is_better=False),
    )

    # run the ModelRanker to retrieve a ranking, using refit=True
    model_ranking: ModelRanking = model_ranker.run(sample=sample, refit=True)

    # check we have models fitted differently:
    # 1. fetch the coefficients:
    # noinspection PyUnresolvedReferences
    coefs = [m.estimator.coef_ for m in model_ranking]

    # 2. assert coefficients are different:
    assert not np.array_equal(coefs[0], coefs[1])


def test_model_ranker_no_preprocessing() -> None:
    warnings.filterwarnings("ignore", message="numpy.dtype size changed")
    warnings.filterwarnings("ignore", message="numpy.ufunc size changed")
    warnings.filterwarnings("ignore", message="You are accessing a training score")

    # define a yield-engine circular CV:
    my_cv = CircularCrossValidator(test_ratio=0.21, num_folds=50)

    # define parameters and model
    models = ModelZoo(
        [
            Model(
                estimator=SVC(gamma="scale"),
                parameter_grid={"kernel": ("linear", "rbf"), "C": [1, 10]},
            )
        ]
    )

    model_ranker: ModelRanker = ModelRanker(zoo=models, cv=my_cv)

    #  load sklearn test-data and convert to pd
    iris = datasets.load_iris()
    test_data = pd.DataFrame(
        data=np.c_[iris["data"], iris["target"]],
        columns=iris["feature_names"] + ["target"],
    )
    test_sample: Sample = Sample(observations=test_data, target_name="target")

    model_ranking: ModelRanking = model_ranker.run(test_sample)

    log.info(f"\n{model_ranking.summary_report()}")

    assert (
        model_ranking.model(BEST_MODEL_RANK).score >= 0.8
    ), "Expected a performance of at least 0.8"
