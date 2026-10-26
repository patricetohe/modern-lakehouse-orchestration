"""Sanity tests for the dbt mart layer (dim_customers, fact_orders).

Like test_staging_models.py / test_intermediate_models.py, these checks
only touch the filesystem, stdlib and PyYAML — they don't require dbt or
Postgres, so they can run outside the project's Docker Compose stack.
Full compilation and the column tests declared in schema.yml are
exercised against Postgres once the stack is up.
"""
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = REPO_ROOT / "dbt_project" / "models" / "marts"


class TestMartModelFiles(unittest.TestCase):
    def test_dim_customers_sql_exists_and_selects_from_staging(self):
        path = MARTS_DIR / "dim_customers.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("ref('stg_customers')", sql)
        self.assertIn("customer_id", sql)

    def test_fact_orders_sql_exists_and_builds_on_intermediate(self):
        path = MARTS_DIR / "fact_orders.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("ref('int_orders_deduped')", sql)
        self.assertIn("order_id", sql)
        self.assertIn("customer_id", sql)
        self.assertIn("amount", sql)

    def test_mart_models_do_not_select_from_sources_directly(self):
        # Marts should build on staging/intermediate refs, never go
        # straight to a source(), keeping the layering intact.
        for sql_path in MARTS_DIR.glob("*.sql"):
            sql = sql_path.read_text()
            self.assertNotIn("source(", sql)


class TestMartSchemaYml(unittest.TestCase):
    def setUp(self):
        path = MARTS_DIR / "schema.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            self.config = yaml.safe_load(f)
        self.models = {m["name"]: m for m in self.config["models"]}

    def test_schema_yml_covers_both_mart_models(self):
        self.assertEqual(self.config["version"], 2)
        self.assertEqual({"dim_customers", "fact_orders"}, set(self.models))

    def test_dim_customers_customer_id_is_unique_and_not_null(self):
        columns = {c["name"]: c for c in self.models["dim_customers"]["columns"]}
        self.assertIn("customer_id", columns)
        tests = columns["customer_id"].get("tests", [])
        self.assertIn("unique", tests)
        self.assertIn("not_null", tests)

    def test_fact_orders_order_id_is_unique_and_not_null(self):
        columns = {c["name"]: c for c in self.models["fact_orders"]["columns"]}
        self.assertIn("order_id", columns)
        tests = columns["order_id"].get("tests", [])
        self.assertIn("unique", tests)
        self.assertIn("not_null", tests)

    def test_fact_orders_customer_id_relates_to_dim_customers(self):
        columns = {c["name"]: c for c in self.models["fact_orders"]["columns"]}
        tests = columns["customer_id"].get("tests", [])
        relationship_tests = [t for t in tests if isinstance(t, dict) and "relationships" in t]
        self.assertEqual(len(relationship_tests), 1)
        rel = relationship_tests[0]["relationships"]
        self.assertEqual(rel["field"], "customer_id")
        self.assertIn("dim_customers", rel["to"])

    def test_fact_orders_columns_match_sql_select(self):
        sql = (MARTS_DIR / "fact_orders.sql").read_text()
        declared = {c["name"] for c in self.models["fact_orders"]["columns"]}
        for col in declared:
            self.assertIn(col, sql, f"{col} declared in schema.yml but not selected in fact_orders.sql")


if __name__ == "__main__":
    unittest.main()
