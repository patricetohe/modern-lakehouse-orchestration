"""Lightweight sanity tests for the project skeleton increment.

These checks only touch the filesystem and stdlib/PyYAML — they don't require
dbt, Airflow or Great Expectations to be installed, so they can run outside
the project's Docker Compose stack. Full pipeline behavior (dbt build,
DAG execution, GE checkpoints) is exercised in the Docker environment as
later roadmap items land.
"""
import csv
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDbtProjectSkeleton(unittest.TestCase):
    def test_dbt_project_yml_is_valid(self):
        path = REPO_ROOT / "dbt_project" / "dbt_project.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            config = yaml.safe_load(f)
        self.assertEqual(config["name"], "modern_lakehouse")
        self.assertEqual(config["profile"], "modern_lakehouse")
        self.assertIn("models", config["model-paths"])

    def test_profiles_yml_defines_target(self):
        path = REPO_ROOT / "dbt_project" / "profiles.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            profiles = yaml.safe_load(f)
        self.assertIn("modern_lakehouse", profiles)
        self.assertEqual(profiles["modern_lakehouse"]["target"], "dev")
        self.assertIn("dev", profiles["modern_lakehouse"]["outputs"])


class TestSeeds(unittest.TestCase):
    def test_raw_orders_seed_has_expected_columns_and_rows(self):
        path = REPO_ROOT / "seeds" / "raw_orders.csv"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertGreater(len(rows), 0)
        expected_columns = {
            "order_id",
            "customer_id",
            "order_date",
            "status",
            "amount",
            "channel",
        }
        self.assertEqual(expected_columns, set(reader.fieldnames))


class TestAirflowDagSkeleton(unittest.TestCase):
    def test_dag_file_declares_expected_tasks_and_dependencies(self):
        path = REPO_ROOT / "dags" / "dbt_pipeline_dag.py"
        self.assertTrue(path.exists(), f"missing {path}")
        source = path.read_text()
        self.assertIn('DAG_ID = "modern_lakehouse_dbt_pipeline"', source)
        for task_id in [
            "seed_raw_data",
            "run_staging_models",
            "run_intermediate_models",
            "run_mart_models",
            "run_quality_checks",
        ]:
            self.assertIn(task_id, source)
        # Dependency chain declared with >> operators
        self.assertIn("seed_raw_data >> run_staging_models", source)
        self.assertIn("run_mart_models >> run_quality_checks", source)


class TestGreatExpectationsSkeleton(unittest.TestCase):
    def test_ge_config_is_valid_yaml_with_datasource(self):
        path = REPO_ROOT / "great_expectations" / "great_expectations.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            config = yaml.safe_load(f)
        self.assertIn("lakehouse_postgres", config["datasources"])
        self.assertEqual(config["expectations_store_name"], "expectations_store")


if __name__ == "__main__":
    unittest.main()
