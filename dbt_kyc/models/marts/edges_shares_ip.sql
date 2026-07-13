-- Graph edge: Customers sharing the same IP address
SELECT
    a.customer_id AS source_node_id,
    b.customer_id AS target_node_id,
    a.ip_address AS shared_ip_id,
    'SHARES_IP' AS relationship_type,
    CURRENT_TIMESTAMP AS created_at
FROM {{ ref('stg_customers') }} a
INNER JOIN {{ ref('stg_customers') }} b
    ON a.ip_address = b.ip_address
    AND a.customer_id < b.customer_id
WHERE a.ip_address IS NOT NULL
  AND a.ip_address != ''
