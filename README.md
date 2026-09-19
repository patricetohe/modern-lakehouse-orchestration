# Modern Lakehouse Orchestration

A batch ELT lakehouse demo showing a complete, orchestrated pipeline: **raw data → dbt (staging/intermediate/marts) → Iceberg tables → Airflow orchestration → Great Expectations data quality gates.**

## Architecture

```
Raw CSV/seed data --> Staging (dbt) --> Intermediate (dbt, joins/dedup) --> Marts (dbt, star schema)
                                                    |
                                    Great Expectations validation gates
                                                    |
                                        Orchestrated end-to-end by Airflow
```

- **dbt_project/** — staging, intermediate and mart models
- **dags/** — Airflow DAGs orchestrating the dbt run and quality checks
- **great_expectations/** — data quality suites
- **seeds/** — sample raw data
- **docs/** — architecture notes

## Status

Built incrementally — see [ROADMAP.md](ROADMAP.md) for the current backlog.

## Stack

dbt, Apache Airflow, Apache Iceberg, Great Expectations, Postgres/MinIO, Docker Compose.
