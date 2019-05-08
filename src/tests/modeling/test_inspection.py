import warnings

import numpy as np
import pandas as pd
from lightgbm.sklearn import LGBMClassifier
from sklearn import datasets
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC

from yieldengine.loading.sample import Sample
from yieldengine.modeling.inspection import ModelInspector
from yieldengine.modeling.selection import (
    BEST_MODEL_RANK,
    Model,
    ModelRanker,
    ModelRanking,
    ModelZoo,
    RankedModel,
)
from yieldengine.modeling.validation import CircularCrossValidator


def test_model_inspection() -> None:
    warnings.filterwarnings("ignore", message="numpy.dtype size changed")
    warnings.filterwarnings("ignore", message="numpy.ufunc size changed")
    warnings.filterwarnings("ignore", message="You are accessing a training score")

    N_FOLDS = 5
    TEST_RATIO = 0.2

    # define a yield-engine circular CV:
    test_cv = CircularCrossValidator(test_ratio=TEST_RATIO, num_folds=N_FOLDS)

    # define parameters and models
    models = ModelZoo(
        [
            Model(
                estimator=SVC(gamma="scale"),
                parameter_grid={"kernel": ("linear", "rbf"), "C": [1, 10]},
            ),
            Model(
                estimator=LGBMClassifier(),
                parameter_grid={
                    "max_depth": (1, 2, 5),
                    "min_split_gain": (0.1, 0.2, 0.5),
                    "num_leaves": (2, 3),
                },
            ),
        ]
    )

    model_ranker: ModelRanker = ModelRanker(zoo=models, cv=test_cv)

    #  load sklearn test-data and convert to pd
    iris = datasets.load_iris()
    test_data = pd.DataFrame(
        data=np.c_[iris["data"], iris["target"]],
        columns=iris["feature_names"] + ["target"],
    )
    test_sample: Sample = Sample(observations=test_data, target_name="target")

    model_ranking: ModelRanking = model_ranker.run(test_sample)

    ranked_model: RankedModel = model_ranking.get_rank(BEST_MODEL_RANK)

    pipeline = make_pipeline(ranked_model.estimator)

    mi = ModelInspector(pipeline=pipeline, cv=test_cv, sample=test_sample)

    predictions_df: pd.DataFrame = mi.predictions_for_all_samples()

    assert ModelInspector.F_FOLD_START in predictions_df.columns
    assert ModelInspector.F_PREDICTION in predictions_df.columns

    # check number of fold-starts
    assert len(predictions_df[ModelInspector.F_FOLD_START].unique()) == N_FOLDS

    # check correct number of rows
    assert len(predictions_df) == (len(test_sample) * TEST_RATIO * N_FOLDS)
