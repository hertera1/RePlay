from typing import Optional

import joblib
import pandas as pd
import numpy as np
from pyspark.sql import DataFrame

from replay.models.base_rec import Recommender
from replay.utils import to_csr, convert2spark
from replay.constants import REC_SCHEMA


class ImplicitWrap(Recommender):
    """Wrapper for `implicit
    <https://github.com/benfred/implicit>`_

    Example:

    >>> import implicit
    >>> model = implicit.als.AlternatingLeastSquares(factors=5)
    >>> als = ImplicitWrap(model)

    This way you can use implicit models as any other in replay
    with conversions made under the hood.

    >>> import pandas as pd
    >>> from replay.utils import convert2spark
    >>> df = pd.DataFrame({"user_idx": [1, 1, 2, 2], "item_idx": [1, 2, 2, 3], "relevance": [1, 1, 1, 1]})
    >>> df = convert2spark(df)
    >>> als.fit_predict(df, 1, users=[1])[["user_idx", "item_idx"]].toPandas()
       user_idx  item_idx
    0         1         3
    """

    def __init__(self, model):
        """Provide initialized ``implicit`` model."""
        self.model = model
        self.logger.info(
            "The model is a wrapper of a non-distributed model which may affect performance"
        )
        self.csr_log = None

    @property
    def _init_args(self):
        return {"model": None}

    def _save_model(self, path: str):
        joblib.dump(self.model, path)

    def _load_model(self, path: str):
        self.model = joblib.load(path)

    def _fit(
        self,
        log: DataFrame,
        user_features: Optional[DataFrame] = None,
        item_features: Optional[DataFrame] = None,
    ) -> None:
        matrix = to_csr(log)
        self.csr_log = matrix
        self.model.fit(matrix)

    # pylint: disable=too-many-arguments
    def _predict(
        self,
        log: DataFrame,
        k: int,
        users: DataFrame,
        items: DataFrame,
        user_features: Optional[DataFrame] = None,
        item_features: Optional[DataFrame] = None,
        filter_seen_items: bool = True,
    ) -> DataFrame:
        def predict_by_user(pandas_df: pd.DataFrame) -> pd.DataFrame:
            user = int(pandas_df["user_idx"].iloc[0])
            ids, rel = model.recommend(
                user, user_item_data[user], k, filter_seen_items, items_to_drop
            )
            return pd.DataFrame(
                {
                    "user_idx": [user] * len(ids),
                    "item_idx": ids,
                    "relevance": rel,
                }
            )

        items_to_drop = (
            log.select("item_idx")
            .subtract(items)
            .select("item_idx")
            .toPandas()
            .item_idx.to_list()
        )
        user_item_data = to_csr(log).tocsr()
        model = self.model
        return (
            users.select("user_idx")
            .groupby("user_idx")
            .applyInPandas(predict_by_user, REC_SCHEMA)
        )

    def _predict_pairs(
        self,
        pairs: DataFrame,
        log: Optional[DataFrame] = None,
        user_features: Optional[DataFrame] = None,
        item_features: Optional[DataFrame] = None,
    ) -> DataFrame:

        user_plays_pred = to_csr(log) if log else self.csr_log

        users = pairs.select("user_idx").distinct().toPandas().user_idx.to_list()
        items = pairs.select("item_idx").distinct().toPandas().item_idx.to_list()
        item_grid, rel = self.model.recommend(
            users, user_plays_pred[users], len(items), False, items=items
        )
        user_grid = np.repeat(np.array(users)[:, np.newaxis], len(items), axis=1)
        res = np.stack([user_grid, item_grid, rel], axis=2).reshape(-1, 3)
        res_df = pd.DataFrame(res, columns=["user_idx", "item_idx", "relevance"])
        res_df = res_df.astype(dtype={"user_idx": "int64",
                                      "item_idx": "int64", "relevance": "float64"})
        res_spark = convert2spark(res_df)

        return res_spark
