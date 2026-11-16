"""Unit tests for the real dbt invocations wired into the Airflow DAG.

dags/dbt_pipeline_dag.py keeps its dbt commands in a plain TASK_COMMANDS
dict (built with _dbt_command()) specifically so this module -- and the
DAG itself -- can be exercised without apache-airflow installed. CI does
not install airflow (see .github/workflows/ci.yml), so these tests import
the dag module directly rather than constructing a live DAG object.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DAG_MODULE_PATH = REPO_ROOT / "dags" / "dbt_pipeline_dag.py"


def _load_dag_module():
    spec = importlib.util.spec_from_file_location("dbt_pipeline_dag", DAG_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dag_module = _load_dag_module()


class TestDbtTaskCommands(unittest.TestCase):
    def test_every_task_id_has_a_command(self):
        for task_id in dag_module.TASK_IDS:
            self.assertIn(task_id, dag_module.TASK_COMMANDS)

    def test_seed_raw_data_runs_dbt_seed(self):
        command = dag_module.TASK_COMMANDS["seed_raw_data"]
        self.assertIn("dbt seed", command)

    def test_run_staging_models_selects_staging_layer(self):
        command = dag_module.TASK_COMMANDS["run_staging_models"]
        self.assertIn("dbt run", command)
        self.assertIn("--select staging", command)

    def test_run_intermediate_models_compiles_rather_than_runs(self):
        # The intermediate layer is +materialized: ephemeral (dbt_project.yml):
        # it has no relation of its own, so this task compiles it to validate
        # the SQL instead of running a `dbt run` that would build nothing.
        command = dag_module.TASK_COMMANDS["run_intermediate_models"]
        self.assertIn("dbt compile", command)
        self.assertIn("--select intermediate", command)
        self.assertNotIn("dbt run", command)

    def test_run_mart_models_selects_marts_layer(self):
        command = dag_module.TASK_COMMANDS["run_mart_models"]
        self.assertIn("dbt run", command)
        self.assertIn("--select marts", command)

    def test_run_quality_checks_runs_dbt_test(self):
        command = dag_module.TASK_COMMANDS["run_quality_checks"]
        self.assertIn("dbt test", command)

    def test_all_commands_are_pinned_to_the_mounted_project_dir(self):
        for task_id, command in dag_module.TASK_COMMANDS.items():
            self.assertIn(f"--project-dir {dag_module.DBT_PROJECT_DIR}", command)
            self.assertIn(f"--profiles-dir {dag_module.DBT_PROJECT_DIR}", command)


class TestBuildDagWithoutAirflow(unittest.TestCase):
    def test_build_dag_raises_clear_error_when_airflow_missing(self):
        # In this test environment apache-airflow is not installed (same as
        # CI), so the module's DAG/BashOperator fall back to None and
        # build_dag() must fail loudly rather than raising an unrelated
        # AttributeError/TypeError deeper in Airflow's own code.
        if dag_module.DAG is not None:
            self.skipTest("apache-airflow is installed; this guard isn't exercised")
        with self.assertRaises(ImportError):
            dag_module.build_dag()


if __name__ == "__main__":
    unittest.main()
