-- Singular dbt test: fact_orders.amount must never be negative.
--
-- The generic `not_null` test on fact_orders.amount (see
-- models/marts/schema.yml) only guards against missing values. A
-- cancelled or refunded order can legitimately have an amount of 0, but
-- a negative amount would mean a data quality bug upstream (e.g. a bad
-- refund adjustment landing in the raw seed/source) that no generic
-- column test catches. This test fails (returns rows) if any such row
-- exists.

select
    order_id,
    customer_id,
    amount
from {{ ref('fact_orders') }}
where amount < 0
