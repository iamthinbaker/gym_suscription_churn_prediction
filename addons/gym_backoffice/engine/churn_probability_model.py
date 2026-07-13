"""
Modelo de predicción de probabilidad de churn para el gimnasio, implementado
a partir de ``experiments/churn_prediction.ipynb``.

``ChurnProbabilityModel`` expone una interfaz al estilo scikit-learn (``fit``,
``predict``, ``predict_proba``, ``save_model``, ``load_model``) para poder
integrarse en el motor de Odoo sin arrastrar el notebook.

Este modelo NO hace feature engineering — espera recibir ``X`` ya con las
features finales (ver ``engine/feature_engineering.FeatureEngineer``).
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.compose import make_column_selector
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import FunctionTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OrdinalEncoder


class NotFittedError(RuntimeError):
    """El modelo no está entrenado ni cargado todavía."""


class ChurnProbabilityModel:
    """Modelo de churn (Random Forest) con interfaz al estilo scikit-learn.

    ``self.model`` es un único ``Pipeline`` que encadena el preprocesador
    (``ColumnTransformer``) y el ``RandomForestClassifier``.

    Espera que ``X`` ya venga con las features finales (ver
    ``engine/feature_engineering.FeatureEngineer``), no con el DataFrame
    maestro en crudo.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

        self.model: Pipeline | None = None
        self.feature_columns_: list[str] | None = None
        self.transformed_feature_names_: list[str] | None = None

    @staticmethod
    def _bool_to_int(x):
        """Reemplaza el lambda del notebook: debe ser una función con nombre
        para que el pipeline se pueda serializar con joblib/pickle."""
        return x.astype(int)

    @staticmethod
    def build_preprocessor() -> ColumnTransformer:
        """Mismo ``ColumnTransformer`` que la celda de preprocesado del notebook."""
        return ColumnTransformer(
            [
                (
                    "num",
                    Pipeline(
                        [
                            ("imp", SimpleImputer(strategy="median")),
                            ("scl", StandardScaler()),
                        ]
                    ),
                    make_column_selector(dtype_include="number"),  # type: ignore[arg-type]
                ),
                (
                    "cat",
                    Pipeline(
                        [
                            ("imp", SimpleImputer(strategy="most_frequent")),
                            (
                                "enc",
                                OrdinalEncoder(
                                    handle_unknown="use_encoded_value", unknown_value=-1
                                ),
                            ),
                        ]
                    ),
                    make_column_selector(dtype_include="object"),  # type: ignore[arg-type]
                ),
                (
                    "bin",
                    Pipeline(
                        [
                            ("to_num", FunctionTransformer(ChurnProbabilityModel._bool_to_int)),
                            ("imp", SimpleImputer(strategy="most_frequent")),
                        ]
                    ),
                    make_column_selector(dtype_include="bool"),  # type: ignore[arg-type]
                ),
            ],
            remainder="drop",
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ChurnProbabilityModel":
        """Entrena el modelo. ``X`` debe venir ya con las features finales."""
        self.feature_columns_ = list(X.columns)
        # Orden en el que el ColumnTransformer concatena las columnas
        # transformadas (num, cat, bin) — necesario para poder mapear
        # ``clf.feature_importances_`` de vuelta a nombres de columna.
        self.transformed_feature_names_ = (
            list(X.select_dtypes(include="number").columns)
            + list(X.select_dtypes(include="object").columns)
            + list(X.select_dtypes(include="bool").columns)
        )

        self.model = Pipeline(
            [
                ("prep", self.build_preprocessor()),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=200,
                        max_depth=7,
                        class_weight="balanced",
                        min_samples_leaf=5,
                        n_jobs=-1,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )
        self.model.fit(X, y)

        return self

    def _check_fitted(self):
        if self.model is None:
            raise NotFittedError(
                "ChurnProbabilityModel no está entrenado. Llama a fit() o load_model() antes."
            )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predicción de clase (0 = Activo, 1 = Baja)."""
        self._check_fitted()
        assert self.model is not None
        return np.asarray(self.model.predict(X.reindex(columns=self.feature_columns_)))

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Probabilidades por clase, shape (n_samples, 2), igual que sklearn.

        Si los datos de entrenamiento sólo contenían una clase (p.ej. ningún
        socio dado de baja todavía en el histórico), el clasificador interno
        sólo conoce esa clase y ``predict_proba`` devolvería una única
        columna. Normalizamos siempre a 2 columnas (0 = activo, 1 = baja)
        para que el resto del código pueda seguir indexando ``[:, 1]``.
        """
        self._check_fitted()
        assert self.model is not None
        raw_proba = np.asarray(
            self.model.predict_proba(X.reindex(columns=self.feature_columns_))
        )
        classes = self.model.named_steps["clf"].classes_

        proba = np.zeros((raw_proba.shape[0], 2))
        for col_idx, cls in enumerate(classes):
            proba[:, int(cls)] = raw_proba[:, col_idx]
        return proba

    def get_feature_importances(self) -> list[tuple[str, float]]:
        """Pares ``(feature, importancia)`` según el ``RandomForestClassifier``
        entrenado, ordenados de mayor a menor importancia."""
        self._check_fitted()
        assert self.model is not None
        assert self.transformed_feature_names_ is not None
        importances = self.model.named_steps["clf"].feature_importances_
        pairs: list[tuple[str, float]] = list(
            zip(self.transformed_feature_names_, (float(v) for v in importances))
        )
        pairs.sort(key=lambda pair: pair[1], reverse=True)
        return pairs

    def save_model(self, path: str) -> None:
        """Serializa el modelo entrenado (pipeline + metadatos) a disco."""
        self._check_fitted()
        joblib.dump(
            {
                "model": self.model,
                "feature_columns": self.feature_columns_,
                "transformed_feature_names": self.transformed_feature_names_,
                "random_state": self.random_state,
            },
            path,
        )

    @classmethod
    def load_model(cls, path: str) -> "ChurnProbabilityModel":
        """Carga un modelo previamente guardado con ``save_model``."""
        payload = joblib.load(path)
        instance = cls(random_state=payload["random_state"])
        instance.model = payload["model"]
        instance.feature_columns_ = payload["feature_columns"]
        instance.transformed_feature_names_ = payload["transformed_feature_names"]
        return instance
