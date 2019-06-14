import logging
from typing import *

import pandas as pd

from yieldengine import Sample
from yieldengine.df.transform import DataFrameTransformer
from yieldengine.model.prediction import PredictorCV
from yieldengine.model.selection import ModelEvaluation, ModelGrid, ModelRanker
from yieldengine.model.validation import CircularCrossValidator
from yieldengine.simulation import UnivariateSimulation

log = logging.getLogger(__name__)

N_FOLDS = 5
TEST_RATIO = 0.2


def test_univariate_simulation(
    batch_table: pd.DataFrame,
    regressor_grids: Iterable[ModelGrid],
    sample: Sample,
    simple_preprocessor: DataFrameTransformer,
    available_cpus: int,
) -> None:

    # define the circular cross validator with just 5 folds (to speed up testing)
    circular_cv = CircularCrossValidator(test_ratio=TEST_RATIO, num_folds=N_FOLDS)

    model_ranker: ModelRanker = ModelRanker(
        grids=regressor_grids, cv=circular_cv, scoring="r2"
    )

    # run the ModelRanker to retrieve a ranking
    model_ranking: Sequence[ModelEvaluation] = model_ranker.run(
        sample=sample, n_jobs=available_cpus
    )

    mp = PredictorCV(model=model_ranking[0].model, cv=circular_cv, sample=sample)

    sim = UnivariateSimulation(predictor=mp)

    parameterized_feature = "Step4-6 RawMat Vendor Compound08 Purity (#)"

    res = sim.simulate_yield_change(
        parameterized_feature=parameterized_feature,
        parameter_values=sample.observed_feature_values(
            feature_name=parameterized_feature
        ),
    )

    log.debug(res)
    log.debug(
        UnivariateSimulation.aggregate_simulated_yield_change(
            foldwise_results=res, percentiles=[10, 50, 90]
        )
    )
