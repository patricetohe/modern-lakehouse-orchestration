-- Singular dbt test: an order can never predate the customer's signup.
--
-- The generic `relationships` test on fact_orders.customer_id (see
-- models/marts/schema.yml) only checks that the foreign key exists in
-- dim_customers -- it says nothing about whether the dates are
-- consistent. This test catches the temporal integrity bug where
-- order_date < signup_date, which would mean a customer placed an
-- order before they existed in the system. Fails (returns rows) if any
-- such order/customer pair exists.

select
    f.order_id,
    f.customer_id,
    f.order_date,
    d.signup_date
from {{ ref('fact_orders') }} as f
inner join {{ ref('dim_customers') }} as d
    on f.customer_id = d.customer_id
where f.order_date < d.signup_date
