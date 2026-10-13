with source as (

    select * from {{ source('raw', 'raw_customers') }}

),

renamed as (

    select
        customer_id,
        customer_name,
        email,
        cast(signup_date as date) as signup_date,
        region

    from source

)

select * from renamed
