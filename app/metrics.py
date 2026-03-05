import time
from contextlib import contextmanager
from typing import Iterator
from prometheus_client import Counter, Histogram


PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Total number of model predictions",
    ["result"],
)

PREDICTION_DURATION_SECONDS = Histogram(
    "prediction_duration_seconds",
    "Time spent on ML model inference",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

PREDICTION_ERRORS_TOTAL = Counter(
    "prediction_errors_total",
    "Total number of prediction errors",
    ["error_type"],
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Time spent on PostgreSQL queries",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

MODEL_PREDICTION_PROBABILITY = Histogram(
    "model_prediction_probability",
    "Distribution of predicted violation probability",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)


@contextmanager
def observe_prediction_duration() -> Iterator[None]:
    start_time = time.perf_counter()
    try:
        yield
    finally:
        PREDICTION_DURATION_SECONDS.observe(time.perf_counter() - start_time)


def record_prediction_result(is_violation: bool, probability: float) -> None:
    result_label = "violation" if is_violation else "no_violation"
    PREDICTIONS_TOTAL.labels(result=result_label).inc()
    MODEL_PREDICTION_PROBABILITY.observe(probability)


def record_prediction_error(error_type: str) -> None:
    PREDICTION_ERRORS_TOTAL.labels(error_type=error_type).inc()


@contextmanager
def observe_db_query_duration(query_type: str) -> Iterator[None]:
    start_time = time.perf_counter()
    try:
        yield
    finally:
        DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(time.perf_counter() - start_time)
