-- Graph node: Customer entities
SELECT DISTINCT
    customer_id AS entity_id,
    customer_id,
    full_name,
    date_of_birth,
    national_id,
    'NONE' AS risk_flag,
    CURRENT_TIMESTAMP AS created_at
FROM {{ ref('stg_customers') }}
