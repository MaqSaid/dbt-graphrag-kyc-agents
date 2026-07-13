-- Graph edge: Customers sharing the same phone number
SELECT
    a.customer_id AS source_node_id,
    b.customer_id AS target_node_id,
    a.phone AS shared_phone_id,
    'SHARES_PHONE' AS relationship_type,
    CURRENT_TIMESTAMP AS created_at
FROM {{ ref('stg_customers') }} a
INNER JOIN {{ ref('stg_customers') }} b
    ON a.phone = b.phone
    AND a.customer_id < b.customer_id
WHERE a.phone IS NOT NULL
  AND a.phone != ''
