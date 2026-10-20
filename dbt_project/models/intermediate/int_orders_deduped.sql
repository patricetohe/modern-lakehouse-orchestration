with orders as (

    select * from {{ ref('stg_orders') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by order_id
            order by order_date desc
        ) as _row_num

    from orders

)

select
    order_id,
    customer_id,
    order_date,
    status,
    amount,
    channel

from deduped
where _row_num = 1
