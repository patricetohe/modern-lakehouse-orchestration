# Roadmap

- [x] Project skeleton: dbt_project/, dags/, great_expectations/, seeds/
- [ ] Docker Compose: Airflow (LocalExecutor) + Postgres metadata db
- [ ] Seed raw sample data (CSV) into a staging schema
- [ ] dbt sources.yml + staging models
- [ ] dbt intermediate models (joins, deduplication)
- [ ] dbt mart models (fact/dimension star schema)
- [ ] dbt tests: unique, not_null, relationships on key models
- [ ] Airflow DAG orchestrating `dbt build` end to end
- [ ] Great Expectations suite on the staging layer
- [ ] dbt source freshness checks
- [ ] Incremental model for the largest fact table
- [ ] MinIO + Iceberg REST catalog for the raw layer (time travel demo)
- [ ] Airflow sensor waiting for upstream file arrival
- [ ] Failure alerting hook in the DAG (logged, Slack-webhook-ready)
- [ ] dbt docs generation + served via a simple container
- [ ] CI: `dbt build` + Great Expectations validation on every PR
- [ ] Data contract (YAML) between source and staging layer
- [ ] Backfill DAG for historical reprocessing by date range
- [ ] Architecture README with DAG diagram
- [ ] Notes: full-refresh vs incremental cost/performance tradeoffs

- [x] GitHub Actions CI: run unit tests on every PR
