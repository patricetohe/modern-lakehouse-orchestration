"""Skeleton Airflow DAG for the modern_lakehouse dbt pipeline.

This DAG lays out the intended orchestration shape for the project:

    seed_raw_data -> run_staging_models -> run_intermediate_models
                   -> run_mart_models -> run_quality_checks

Each task is currently an EmptyOperator placeholder. The real dbt/Great
Expectations invocations are wired in by later roadmap items ("Airflow DAG
orchestrating `dbt build` end to end" and "Great Expectations suite on the
staging layer"). Keeping the DAG importable and dependency-correct now means
those later steps only need to swap placeholders for real operators.

Running this DAG for real requires the project's Docker Compose stack
(Airflow + Postgres) — see docker-compose.yml.
"""
from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.empty import EmptyOperator
except ImportError:  # pragma: no cover - airflow not installed outside Docker
    DAG = None
    EmptyOperator = None

DAG_ID = "modern_lakehouse_dbt_pipeline"

DEFAULT_ARGS = {
    "owner": "modern_lakehouse",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

TASK_IDS = [
    "seed_raw_data",
    "run_staging_models",
    "run_intermediate_models",
    "run_mart_models",
    "run_quality_checks",
]


def build_dag() -> "DAG":
    """Construct the skeleton DAG. Requires apache-airflow to be installed."""
    if DAG is None:
        raise ImportError(
            "apache-airflow is not installed in this environment; "
            "run this inside the project's Docker Compose stack."
        )

    with DAG(
        dag_id=DAG_ID,
        description="Batch ELT lakehouse pipeline: seed -> dbt -> quality gates",
        default_args=DEFAULT_ARGS,
        schedule=None,  # manual trigger until the roadmap wires up a cadence
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["dbt", "lakehouse", "skeleton"],
    ) as dag:
        seed_raw_data = EmptyOperator(task_id="seed_raw_data")
        run_staging_models = EmptyOperator(task_id="run_staging_models")
        run_intermediate_models = EmptyOperator(task_id="run_intermediate_models")
        run_mart_models = EmptyOperator(task_id="run_mart_models")
        run_quality_checks = EmptyOperator(task_id="run_quality_checks")

        seed_raw_data >> run_staging_models >> run_intermediate_models
        run_intermediate_models >> run_mart_models >> run_quality_checks

    return dag


if DAG is not None:
    dag = build_dag()
