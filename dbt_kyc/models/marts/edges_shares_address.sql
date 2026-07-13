-- Graph edge: Customers sharing the same address
SELECT
    a.customer_id AS source_node_id,
    b.customer_id AS target_node_id,
    a.address_hash AS shared_address_id,
    'SHARES_ADDRESS' AS relationship_type,
    CURRENT_TIMESTAMP AS created_at
FROM {{ ref('stg_customers') }} a
INNER JOIN {{ ref('stg_customers') }} b
    ON a.address_hash = b.address_hash
    AND a.customer_id < b.customer_id
