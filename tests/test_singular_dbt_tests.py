"""Sanity tests for the dbt singular (custom) tests on the mart layer.

Generic column tests (unique/not_null/relationships/accepted_values) are
declared in schema.yml for every key model -- see test_staging_models.py,
test_intermediate_models.py and test_mart_models.py. Those can't express
business-rule checks that span two columns or two models, which is what
the singular tests in dbt_project/tests/ are for:

  - assert_fact_orders_amount_non_negative.sql
  - assert_no_orders_before_customer_signup.sql

Like the other test modules in this suite, these checks only touch the
filesystem, stdlib and PyYAML/csv -- they don't require dbt or Postgres.
As a stand-in for actually running `dbt test` (not available without the
project's Docker Compose stack), this module also replicates each
singular test's predicate in plain Python against the current seed CSVs,
so a real regression in the sample data would fail CI even before the
Postgres-backed `dbt test` run exists.
"""
import csv
import re
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_TESTS_DIR = REPO_ROOT / "dbt_project" / "tests"
SEEDS_DIR = REPO_ROOT / "seeds"


def _read_csv_rows(path: Path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class TestSingularTestFilesExist(unittest.TestCase):
    def test_amount_non_negative_test_file_exists_and_targets_fact_orders(self):
        path = DBT_TESTS_DIR / "assert_fact_orders_amount_non_negative.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("ref('fact_orders')", sql)
        self.assertIn("amount", sql)
        self.assertIn("< 0", sql)

    def test_orders_before_signup_test_file_exists_and_joins_both_models(self):
        path = DBT_TESTS_DIR / "assert_no_orders_before_customer_signup.sql"
        self.assertTrue(path.exists(), f"missing {path}")
        sql = path.read_text()
        self.assertIn("ref('fact_orders')", sql)
        self.assertIn("ref('dim_customers')", sql)
        self.assertIn("order_date", sql)
        self.assertIn("signup_date", sql)

    def test_singular_test_files_select_only_no_dml(self):
        # A dbt singular test must be a bare SELECT: it fails the build
        # if it contains anything that mutates data.
        forbidden = re.compile(r"\b(insert|update|delete|drop|truncate|merge)\b", re.IGNORECASE)
        for sql_path in DBT_TESTS_DIR.glob("*.sql"):
            sql = sql_path.read_text()
            self.assertIsNone(
                forbidden.search(sql), f"{sql_path.name} looks like it contains DML, not a plain SELECT"
            )
            self.assertRegex(sql.lower(), r"\bselect\b", f"{sql_path.name} has no SELECT statement")


class TestSingularTestPredicatesAgainstSeedData(unittest.TestCase):
    """Replicates each singular test's predicate in Python against the raw
    seed CSVs that feed stg_orders/stg_customers -> fact_orders/dim_customers,
    so a real data regression is caught without needing dbt + Postgres."""

    def setUp(self):
        self.orders = _read_csv_rows(SEEDS_DIR / "raw_orders.csv")
        self.customers = _read_csv_rows(SEEDS_DIR / "raw_customers.csv")
        self.signup_by_customer = {
            c["customer_id"]: date.fromisoformat(c["signup_date"]) for c in self.customers
        }

    def test_no_seed_order_has_a_negative_amount(self):
        negative = [o for o in self.orders if float(o["amount"]) < 0]
        self.assertEqual(
            negative, [], f"seed data has order(s) with a negative amount: {negative}"
        )

    def test_no_seed_order_predates_its_customers_signup(self):
        violations = []
        for order in self.orders:
            customer_id = order["customer_id"]
            signup = self.signup_by_customer.get(customer_id)
            if signup is None:
                continue
            order_date = date.fromisoformat(order["order_date"])
            if order_date < signup:
                violations.append((order["order_id"], customer_id, order_date, signup))
        self.assertEqual(
            violations, [], f"seed data has order(s) placed before their customer signed up: {violations}"
        )


if __name__ == "__main__":
    unittest.main()
