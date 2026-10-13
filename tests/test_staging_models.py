"""Sanity tests for the dbt staging layer (sources.yml + stg_* models).

These checks only touch the filesystem, stdlib and PyYAML — they don't
require dbt or Postgres, so they can run outside the project's Docker
Compose stack. Full compilation and the column tests declared in
schema.yml are exercised against Postgres once the stack is up.
"""
import csv
import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGING_DIR = REPO_ROOT / "dbt_project" / "models" / "staging"
SEEDS_DIR = REPO_ROOT / "seeds"


def _read_csv_fieldnames(path: Path):
    with open(path, newline="") as f:
        return set(csv.DictReader(f).fieldnames)


class TestSourcesYml(unittest.TestCase):
    def test_sources_yml_is_valid_and_declares_raw_schema(self):
        path = STAGING_DIR / "_staging__sources.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            config = yaml.safe_load(f)

        self.assertEqual(config["version"], 2)
        sources = {s["name"]: s for s in config["sources"]}
        self.assertIn("raw", sources)
        self.assertEqual(sources["raw"]["schema"], "raw")

        table_names = {t["name"] for t in sources["raw"]["tables"]}
        self.assertEqual({"raw_customers", "raw_orders"}, table_names)


class TestStagingModelFiles(unittest.TestCase):
    def test_stg_customers_sql_exists_and_selects_from_source(self):
        path = STAGING_DIR / "stg_customers.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("source('raw', 'raw_customers')", sql)
        self.assertIn("customer_id", sql)

    def test_stg_orders_sql_exists_and_selects_from_source(self):
        path = STAGING_DIR / "stg_orders.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("source('raw', 'raw_orders')", sql)
        self.assertIn("order_id", sql)

    def test_staging_models_do_not_reference_raw_tables_directly(self):
        # Staging models must go through source(), never a hardcoded
        # raw.raw_* table reference, so the DAG stays source()-driven.
        for sql_path in STAGING_DIR.glob("stg_*.sql"):
            sql = sql_path.read_text()
            self.assertNotRegex(
                sql,
                r"from\s+raw\.raw_",
                f"{sql_path.name} should select from source(), not a raw table directly",
            )


class TestStagingSchemaYml(unittest.TestCase):
    def setUp(self):
        path = STAGING_DIR / "schema.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            self.config = yaml.safe_load(f)
        self.models = {m["name"]: m for m in self.config["models"]}

    def test_schema_yml_covers_both_staging_models(self):
        self.assertEqual(self.config["version"], 2)
        self.assertEqual({"stg_customers", "stg_orders"}, set(self.models))

    def test_stg_customers_columns_match_between_sql_select_and_schema(self):
        sql = (STAGING_DIR / "stg_customers.sql").read_text()
        declared = {c["name"] for c in self.models["stg_customers"]["columns"]}
        for col in declared:
            self.assertIn(col, sql, f"{col} declared in schema.yml but not selected in stg_customers.sql")

    def test_stg_orders_columns_match_between_sql_select_and_schema(self):
        sql = (STAGING_DIR / "stg_orders.sql").read_text()
        declared = {c["name"] for c in self.models["stg_orders"]["columns"]}
        for col in declared:
            self.assertIn(col, sql, f"{col} declared in schema.yml but not selected in stg_orders.sql")

    def test_primary_keys_are_tested_unique_and_not_null(self):
        for model_name, pk in (("stg_customers", "customer_id"), ("stg_orders", "order_id")):
            columns = {c["name"]: c for c in self.models[model_name]["columns"]}
            self.assertIn(pk, columns)
            tests = columns[pk].get("tests", [])
            self.assertIn("unique", tests)
            self.assertIn("not_null", tests)

    def test_stg_orders_customer_id_relates_to_stg_customers(self):
        columns = {c["name"]: c for c in self.models["stg_orders"]["columns"]}
        tests = columns["customer_id"].get("tests", [])
        relationship_tests = [t for t in tests if isinstance(t, dict) and "relationships" in t]
        self.assertEqual(len(relationship_tests), 1)
        rel = relationship_tests[0]["relationships"]
        self.assertEqual(rel["field"], "customer_id")
        self.assertIn("stg_customers", rel["to"])


class TestStagingModelsStayConsistentWithSeeds(unittest.TestCase):
    """The staging layer renames/casts raw seed columns; every column it
    selects should trace back to a real seed column."""

    def test_stg_customers_columns_are_subset_of_raw_customers_seed(self):
        seed_columns = _read_csv_fieldnames(SEEDS_DIR / "raw_customers.csv")
        sql = (STAGING_DIR / "stg_customers.sql").read_text()
        renamed_block = sql.split("renamed as (")[1]
        select_columns = {
            line.strip().rstrip(",")
            for line in renamed_block.splitlines()
            if line.strip() and not line.strip().startswith(("select", "from", ")"))
        }
        # Strip "cast(x as y) as x" / "x as y" down to the bare column names.
        bare_names = set()
        for col in select_columns:
            match = re.search(r"as\s+(\w+)\s*$", col)
            bare_names.add(match.group(1) if match else col)
        self.assertTrue(bare_names.issubset(seed_columns), bare_names - seed_columns)

    def test_stg_orders_columns_are_subset_of_raw_orders_seed(self):
        seed_columns = _read_csv_fieldnames(SEEDS_DIR / "raw_orders.csv")
        sql = (STAGING_DIR / "stg_orders.sql").read_text()
        renamed_block = sql.split("renamed as (")[1]
        select_columns = {
            line.strip().rstrip(",")
            for line in renamed_block.splitlines()
            if line.strip() and not line.strip().startswith(("select", "from", ")"))
        }
        bare_names = set()
        for col in select_columns:
            match = re.search(r"as\s+(\w+)\s*$", col)
            bare_names.add(match.group(1) if match else col)
        self.assertTrue(bare_names.issubset(seed_columns), bare_names - seed_columns)


if __name__ == "__main__":
    unittest.main()
