with orders as (

    select * from {{ ref('int_orders_deduped') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

joined as (

    select
        orders.order_id,
        orders.customer_id,
        orders.order_date,
        orders.status,
        orders.amount,
        orders.channel,
        customers.customer_name,
        customers.region as customer_region

    from orders
    left join customers
        on orders.customer_id = customers.customer_id

)

select * from joined
