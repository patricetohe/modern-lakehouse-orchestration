with source as (

    select * from {{ source('raw', 'raw_orders') }}

),

renamed as (

    select
        order_id,
        customer_id,
        cast(order_date as date) as order_date,
        status,
        cast(amount as numeric(12, 2)) as amount,
        channel

    from source

)

select * from renamed
