"""Airflow DAG orchestrating the modern_lakehouse dbt pipeline end to end.

    seed_raw_data -> run_staging_models -> run_intermediate_models
                   -> run_mart_models -> run_quality_checks

Each task shells out to `dbt` inside the project's Docker Compose stack
(the dbt project and profile are mounted at DBT_PROJECT_DIR in the
airflow containers -- see docker-compose.yml). Layer boundaries are
expressed with dbt's node selection (`--select staging` / `marts`, which
dbt resolves by matching the model's subfolder), not by hardcoding model
names, so new models added to a layer are picked up automatically.

`run_intermediate_models` uses `dbt compile` rather than `dbt run`: the
intermediate layer is configured `+materialized: ephemeral`
(dbt_project.yml), so it has no relation of its own to build -- it is
inlined as a CTE into whatever selects it. Compiling it on its own
still validates that layer's SQL (refs resolve, no syntax errors)
before the mart layer, which does materialize, builds on top of it.

`run_quality_checks` runs the full dbt test suite: the generic
unique/not_null/relationships tests declared in each layer's schema.yml
plus the singular tests under dbt_project/tests/.

Running this DAG for real requires the project's Docker Compose stack
(Airflow + Postgres) -- see docker-compose.yml. Outside that stack (e.g.
in CI, where apache-airflow is intentionally not installed -- see
.github/workflows/ci.yml) the module still imports cleanly: `DAG` and
`BashOperator` fall back to None and `build_dag()` raises a clear error
instead of crashing at import time.
"""
from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
except ImportError:  # pragma: no cover - airflow not installed outside Docker
    DAG = None
    BashOperator = None

DAG_ID = "modern_lakehouse_dbt_pipeline"

# Where the dbt project (and its profiles.yml) is mounted inside the
# Airflow containers. Matches the `./dbt_project:/opt/airflow/dbt_project`
# volume and `DBT_PROFILES_DIR` in docker-compose.yml.
DBT_PROJECT_DIR = "/opt/airflow/dbt_project"

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


def _dbt_command(*args: str) -> str:
    """Build a `dbt <args>` invocation pinned to this project's dir/profile."""
    return " ".join(
        [
            "dbt",
            *args,
            "--project-dir",
            DBT_PROJECT_DIR,
            "--profiles-dir",
            DBT_PROJECT_DIR,
        ]
    )


# One dbt invocation per DAG task, kept as a plain dict so both build_dag()
# and the unit tests can inspect the exact command without constructing a
# live Airflow DAG (airflow isn't installed in CI -- see module docstring).
TASK_COMMANDS = {
    "seed_raw_data": _dbt_command("seed"),
    "run_staging_models": _dbt_command("run", "--select", "staging"),
    "run_intermediate_models": _dbt_command("compile", "--select", "intermediate"),
    "run_mart_models": _dbt_command("run", "--select", "marts"),
    "run_quality_checks": _dbt_command("test"),
}


def build_dag() -> "DAG":
    """Construct the dbt pipeline DAG. Requires apache-airflow to be installed."""
    if DAG is None or BashOperator is None:
        raise ImportError(
            "apache-airflow is not installed in this environment; "
            "run this inside the project's Docker Compose stack."
        )

    with DAG(
        dag_id=DAG_ID,
        description="Batch ELT lakehouse pipeline: seed -> dbt -> quality gates",
        default_args=DEFAULT_ARGS,
        schedule=None,  # manual trigger until a later roadmap item wires up a cadence
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["dbt", "lakehouse"],
    ) as dag:
        seed_raw_data = BashOperator(
            task_id="seed_raw_data",
            bash_command=TASK_COMMANDS["seed_raw_data"],
        )
        run_staging_models = BashOperator(
            task_id="run_staging_models",
            bash_command=TASK_COMMANDS["run_staging_models"],
        )
        run_intermediate_models = BashOperator(
            task_id="run_intermediate_models",
            bash_command=TASK_COMMANDS["run_intermediate_models"],
        )
        run_mart_models = BashOperator(
            task_id="run_mart_models",
            bash_command=TASK_COMMANDS["run_mart_models"],
        )
        run_quality_checks = BashOperator(
            task_id="run_quality_checks",
            bash_command=TASK_COMMANDS["run_quality_checks"],
        )

        seed_raw_data >> run_staging_models >> run_intermediate_models
        run_intermediate_models >> run_mart_models >> run_quality_checks

    return dag


if DAG is not None:
    dag = build_dag()
