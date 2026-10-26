with customers as (

    select * from {{ ref('stg_customers') }}

)

select
    customer_id,
    customer_name,
    email,
    signup_date,
    region

from customers
