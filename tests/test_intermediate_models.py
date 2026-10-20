"""Sanity tests for the dbt intermediate layer (int_orders_deduped,
int_orders_joined).

Like test_staging_models.py, these checks only touch the filesystem,
stdlib and PyYAML — they don't require dbt or Postgres, so they can run
outside the project's Docker Compose stack. Full compilation and the
column tests declared in schema.yml are exercised against Postgres once
the stack is up.
"""
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERMEDIATE_DIR = REPO_ROOT / "dbt_project" / "models" / "intermediate"


class TestIntermediateModelFiles(unittest.TestCase):
    def test_int_orders_deduped_sql_exists_and_dedups_on_order_id(self):
        path = INTERMEDIATE_DIR / "int_orders_deduped.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("ref('stg_orders')", sql)
        self.assertIn("row_number()", sql.lower())
        self.assertIn("partition by order_id", sql.lower())
        self.assertIn("_row_num = 1", sql)

    def test_int_orders_joined_sql_exists_and_joins_customers(self):
        path = INTERMEDIATE_DIR / "int_orders_joined.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("ref('int_orders_deduped')", sql)
        self.assertIn("ref('stg_customers')", sql)
        self.assertIn("join", sql.lower())
        self.assertIn("customer_id", sql)

    def test_intermediate_models_do_not_select_from_sources_directly(self):
        # Intermediate models should build on staging (ref()), never go
        # straight to a source(), keeping the staging -> intermediate ->
        # marts layering intact.
        for sql_path in INTERMEDIATE_DIR.glob("int_*.sql"):
            sql = sql_path.read_text()
            self.assertNotIn("source(", sql)


class TestIntermediateSchemaYml(unittest.TestCase):
    def setUp(self):
        path = INTERMEDIATE_DIR / "schema.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            self.config = yaml.safe_load(f)
        self.models = {m["name"]: m for m in self.config["models"]}

    def test_schema_yml_covers_both_intermediate_models(self):
        self.assertEqual(self.config["version"], 2)
        self.assertEqual({"int_orders_deduped", "int_orders_joined"}, set(self.models))

    def test_order_id_is_tested_unique_and_not_null_on_both_models(self):
        for model_name in ("int_orders_deduped", "int_orders_joined"):
            columns = {c["name"]: c for c in self.models[model_name]["columns"]}
            self.assertIn("order_id", columns)
            tests = columns["order_id"].get("tests", [])
            self.assertIn("unique", tests)
            self.assertIn("not_null", tests)

    def test_int_orders_deduped_customer_id_relates_to_stg_customers(self):
        columns = {c["name"]: c for c in self.models["int_orders_deduped"]["columns"]}
        tests = columns["customer_id"].get("tests", [])
        relationship_tests = [t for t in tests if isinstance(t, dict) and "relationships" in t]
        self.assertEqual(len(relationship_tests), 1)
        rel = relationship_tests[0]["relationships"]
        self.assertEqual(rel["field"], "customer_id")
        self.assertIn("stg_customers", rel["to"])

    def test_int_orders_joined_columns_match_sql_select(self):
        sql = (INTERMEDIATE_DIR / "int_orders_joined.sql").read_text()
        declared = {c["name"] for c in self.models["int_orders_joined"]["columns"]}
        for col in declared:
            self.assertIn(col, sql, f"{col} declared in schema.yml but not selected in int_orders_joined.sql")


if __name__ == "__main__":
    unittest.main()
