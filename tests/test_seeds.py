"""Sanity tests for the raw seed data increment.

These checks only touch the filesystem and stdlib/PyYAML — they don't
require dbt to be installed, so they can run outside the project's Docker
Compose stack. Full seed loading (``dbt seed``) and the column tests
declared in seeds/schema.yml are exercised against Postgres once the stack
is up.
"""
import csv
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS_DIR = REPO_ROOT / "seeds"


def _read_csv_rows(path: Path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


class TestRawCustomersSeed(unittest.TestCase):
    def test_raw_customers_has_expected_columns_and_rows(self):
        path = SEEDS_DIR / "raw_customers.csv"
        self.assertTrue(path.exists(), f"missing {path}")
        fieldnames, rows = _read_csv_rows(path)
        expected_columns = {
            "customer_id",
            "customer_name",
            "email",
            "signup_date",
            "region",
        }
        self.assertEqual(expected_columns, set(fieldnames))
        self.assertGreater(len(rows), 0)

    def test_customer_id_and_email_are_unique(self):
        _, rows = _read_csv_rows(SEEDS_DIR / "raw_customers.csv")
        ids = [r["customer_id"] for r in rows]
        emails = [r["email"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), "duplicate customer_id in seed")
        self.assertEqual(len(emails), len(set(emails)), "duplicate email in seed")

    def test_no_row_has_a_blank_field(self):
        _, rows = _read_csv_rows(SEEDS_DIR / "raw_customers.csv")
        for row in rows:
            for col, value in row.items():
                self.assertTrue(value, f"blank {col} in raw_customers.csv row {row}")


class TestSeedReferentialIntegrity(unittest.TestCase):
    """raw_orders.customer_id must resolve against raw_customers, mirroring
    the `relationships` test declared in seeds/schema.yml."""

    def test_every_order_customer_id_exists_in_customers_seed(self):
        _, customer_rows = _read_csv_rows(SEEDS_DIR / "raw_customers.csv")
        known_customer_ids = {r["customer_id"] for r in customer_rows}

        _, order_rows = _read_csv_rows(SEEDS_DIR / "raw_orders.csv")
        order_customer_ids = {r["customer_id"] for r in order_rows}

        missing = order_customer_ids - known_customer_ids
        self.assertEqual(
            set(), missing, f"orders reference unknown customer_id(s): {missing}"
        )


class TestSeedSchemaYml(unittest.TestCase):
    def test_schema_yml_is_valid_and_covers_both_seed_tables(self):
        path = SEEDS_DIR / "schema.yml"
        self.assertTrue(path.exists(), f"missing {path}")
        with open(path) as f:
            config = yaml.safe_load(f)

        self.assertEqual(config["version"], 2)
        seed_names = {seed["name"] for seed in config["seeds"]}
        self.assertEqual({"raw_orders", "raw_customers"}, seed_names)

    def test_every_seed_column_in_schema_yml_exists_in_its_csv(self):
        path = SEEDS_DIR / "schema.yml"
        with open(path) as f:
            config = yaml.safe_load(f)

        for seed in config["seeds"]:
            csv_path = SEEDS_DIR / f"{seed['name']}.csv"
            fieldnames, _ = _read_csv_rows(csv_path)
            declared_columns = {col["name"] for col in seed["columns"]}
            self.assertTrue(
                declared_columns.issubset(set(fieldnames)),
                f"schema.yml declares columns not present in {csv_path.name}: "
                f"{declared_columns - set(fieldnames)}",
            )


if __name__ == "__main__":
    unittest.main()
