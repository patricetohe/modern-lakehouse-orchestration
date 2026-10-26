with orders as (

    select * from {{ ref('int_orders_deduped') }}

)

select
    order_id,
    customer_id,
    order_date,
    status,
    channel,
    amount

from orders
