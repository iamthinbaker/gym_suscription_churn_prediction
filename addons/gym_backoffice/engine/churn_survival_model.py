"""
Modelo de predicción de tiempo de vida (supervivencia) para el gimnasio,
implementado a partir de ``experiments/churn_survival_prediction.ipynb``.

Es la contrapartida de ``engine.churn_probability_model.ChurnProbabilityModel``:
en vez de predecir *si* un socio se dará de baja, predice *cuándo* — cuántos
meses más se espera que dure como socio.

``ChurnSurvivalModel`` expone la misma interfaz al estilo scikit-learn que
``ChurnProbabilityModel`` (``fit``, ``predict``, ``predict_proba``, ``save_model``,
``load_model``, ``get_feature_importances``) para poder integrarse en el
motor de Odoo sin arrastrar el notebook.

Este modelo NO hace feature engineering — espera recibir ``X`` ya con las
features finales (ver ``engine/feature_engineering.FeatureEngineer``), y un
``y`` con las columnas ``duration`` (antigüedad en meses) y ``event`` (1 si
la baja fue observada, 0 si el socio sigue activo / está censurado).

Del notebook: los cuatro modelos de supervivencia probados (Cox PH, Weibull
AFT, Log-Normal AFT, Log-Logistic AFT) obtienen un C-index similar, pero
Log-Logistic AFT es el que mejor generaliza (C-index test = 0.593, el más
alto de los cuatro) — es el modelo que usa esta clase.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from lifelines import LogLogisticAFTFitter
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.compose import make_column_selector
from sklearn.preprocessing import FunctionTransformer
from sklearn.preprocessing import OneHotEncoder


class NotFittedError(RuntimeError):
    """El modelo no está entrenado ni cargado todavía."""


class ChurnSurvivalModel:
    """Modelo de tiempo de vida (Log-Logistic AFT) con interfaz al estilo
    scikit-learn, igual que ``ChurnProbabilityModel``.

    ``self.preprocessor`` es el ``ColumnTransformer`` que codifica ``X``, y
    ``self.model`` es el ``LogLogisticAFTFitter`` de ``lifelines`` entrenado
    sobre esas features codificadas más ``duration``/``event``.

    Espera que ``X`` ya venga con las features finales (curadas, sin
    ``duration``/``event``) y que ``y`` sea un DataFrame con las columnas
    ``duration`` (antigüedad en meses) y ``event`` (1 = baja observada,
    0 = censurado / activo), igual que en el notebook.
    """

    def __init__(self, penalizer: float = 0.1, horizon_months: float = 12.0):
        self.penalizer = penalizer
        self.horizon_months = horizon_months

        self.preprocessor: ColumnTransformer | None = None
        self.model: LogLogisticAFTFitter | None = None
        self.feature_columns_: list[str] | None = None

    @staticmethod
    def _bool_to_int(x):
        """Reemplaza el lambda del notebook: debe ser una función con nombre
        para que el preprocesador se pueda serializar con joblib/pickle."""
        return x.astype(int)

    @staticmethod
    def build_preprocessor() -> ColumnTransformer:
        """Mismo ``ColumnTransformer`` que la celda de preprocesado del
        notebook: a diferencia de ``ChurnProbabilityModel`` (árboles), aquí las
        categóricas van con dummies (``OneHotEncoder``) en vez de
        ``OrdinalEncoder``, porque el modelo de supervivencia es lineal en
        el espacio de covariables."""
        return ColumnTransformer(
            [
                (
                    "num",
                    Pipeline([("imp", SimpleImputer(strategy="median"))]),
                    make_column_selector(dtype_include="number"),  # type: ignore[arg-type]
                ),
                (
                    "cat",
                    Pipeline(
                        [
                            ("imp", SimpleImputer(strategy="most_frequent")),
                            (
                                "enc",
                                OneHotEncoder(
                                    drop="first",
                                    dtype=int,
                                    sparse_output=False,
                                    handle_unknown="ignore",
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
                            (
                                "to_num",
                                FunctionTransformer(
                                    ChurnSurvivalModel._bool_to_int,
                                    feature_names_out="one-to-one",
                                ),
                            ),
                            ("imp", SimpleImputer(strategy="most_frequent")),
                        ]
                    ),
                    make_column_selector(dtype_include="bool"),  # type: ignore[arg-type]
                ),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        ).set_output(transform="pandas")

    def fit(self, X: pd.DataFrame, y: pd.DataFrame) -> "ChurnSurvivalModel":
        """Entrena el modelo. ``X`` debe venir ya con las features finales
        (sin ``duration``/``event``); ``y`` debe tener las columnas
        ``duration`` y ``event``."""
        self.feature_columns_ = list(X.columns)

        self.preprocessor = self.build_preprocessor()
        X_trans = self.preprocessor.fit_transform(X)

        train_df = pd.concat(
            [
                X_trans.reset_index(drop=True),
                y[["duration", "event"]].reset_index(drop=True),
            ],
            axis=1,
        )

        self.model = LogLogisticAFTFitter(penalizer=self.penalizer)
        self.model.fit(train_df, duration_col="duration", event_col="event")

        return self

    def _check_fitted(self):
        if self.model is None or self.preprocessor is None:
            raise NotFittedError(
                "ChurnSurvivalModel no está entrenado. Llama a fit() o "
                "load_model() antes."
            )

    def _transform(self, X: pd.DataFrame) -> pd.DataFrame:
        assert self.preprocessor is not None
        return self.preprocessor.transform(X.reindex(columns=self.feature_columns_))

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Tiempo de vida mediano predicho, en meses.

        Se usa la mediana en vez de la esperanza: la esperanza integra la
        curva de supervivencia hasta el infinito y sobreestima sistemática-
        mente la duración más allá del horizonte de seguimiento observado
        (ver notebook, sección 5)."""
        self._check_fitted()
        assert self.model is not None
        X_trans = self._transform(X)
        return np.asarray(self.model.predict_median(X_trans))

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Probabilidad de churn dentro de ``self.horizon_months`` meses,
        shape (n_samples, 2), igual que sklearn: columna 0 = probabilidad de
        seguir activo pasado el horizonte, columna 1 = probabilidad de baja
        dentro del horizonte."""
        self._check_fitted()
        assert self.model is not None
        X_trans = self._transform(X)
        survival = self.model.predict_survival_function(
            X_trans, times=[self.horizon_months]
        )
        prob_survives = np.asarray(survival.loc[self.horizon_months])
        return np.column_stack([prob_survives, 1.0 - prob_survives])

    def get_feature_importances(self) -> list[tuple[str, float]]:
        """Pares ``(feature, coeficiente)`` del parámetro de escala
        (``alpha_``) del ``LogLogisticAFTFitter`` entrenado, ordenados por
        magnitud absoluta de mayor a menor. Un coeficiente negativo acorta
        la vida del socio, uno positivo la alarga."""
        self._check_fitted()
        assert self.model is not None
        coefs = self.model.params_["alpha_"]
        pairs: list[tuple[str, float]] = [
            (name, float(value))
            for name, value in coefs.items()
            if name != "Intercept"
        ]
        pairs.sort(key=lambda pair: abs(pair[1]), reverse=True)
        return pairs

    def save_model(self, path: str) -> None:
        """Serializa el modelo entrenado (preprocesador + modelo +
        metadatos) a disco."""
        self._check_fitted()
        joblib.dump(
            {
                "preprocessor": self.preprocessor,
                "model": self.model,
                "feature_columns": self.feature_columns_,
                "penalizer": self.penalizer,
                "horizon_months": self.horizon_months,
            },
            path,
        )

    @classmethod
    def load_model(cls, path: str) -> "ChurnSurvivalModel":
        """Carga un modelo previamente guardado con ``save_model``."""
        payload = joblib.load(path)
        instance = cls(
            penalizer=payload["penalizer"], horizon_months=payload["horizon_months"]
        )
        instance.preprocessor = payload["preprocessor"]
        instance.model = payload["model"]
        instance.feature_columns_ = payload["feature_columns"]
        return instance
