"""Sanity tests for the Airflow + Postgres docker-compose stack.

These only parse docker-compose.yml with PyYAML to check the service
topology and key settings are correct — they do not require Docker or
actually start any containers, so they run outside the project's Docker
environment. Full end-to-end behavior (webserver reachable, DAG runs)
can only be exercised by actually bringing up the stack with
`docker compose up`.
"""
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDockerComposeStack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "docker-compose.yml"
        assert path.exists(), f"missing {path}"
        with open(path) as f:
            cls.compose = yaml.safe_load(f)

    def test_expected_services_present(self):
        services = self.compose["services"]
        for name in [
            "postgres",
            "airflow-init",
            "airflow-webserver",
            "airflow-scheduler",
        ]:
            self.assertIn(name, services, f"missing service {name}")

    def test_airflow_services_use_local_executor(self):
        anchor_env = self.compose["x-airflow-common"]["environment"]
        self.assertEqual(anchor_env["AIRFLOW__CORE__EXECUTOR"], "LocalExecutor")
        self.assertIn("postgresql+psycopg2://", anchor_env["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"])

    def test_airflow_services_depend_on_postgres(self):
        services = self.compose["services"]
        for name in ["airflow-init", "airflow-webserver", "airflow-scheduler"]:
            depends_on = services[name]["depends_on"]
            self.assertIn("postgres", depends_on)

    def test_webserver_exposes_ui_port(self):
        ports = self.compose["services"]["airflow-webserver"]["ports"]
        self.assertTrue(any(p.startswith("8080:") for p in ports))

    def test_postgres_has_healthcheck_and_volume(self):
        postgres = self.compose["services"]["postgres"]
        self.assertIn("healthcheck", postgres)
        self.assertIn("postgres_data:/var/lib/postgresql/data", postgres["volumes"])

    def test_dag_and_dbt_project_mounted_into_airflow(self):
        volumes = self.compose["x-airflow-common"]["volumes"]
        self.assertIn("./dags:/opt/airflow/dags", volumes)
        self.assertIn("./dbt_project:/opt/airflow/dbt_project", volumes)


if __name__ == "__main__":
    unittest.main()
