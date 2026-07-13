-- Graph node: IP Address entities
SELECT DISTINCT
    md5(ip_address) AS entity_id,
    ip_address,
    CURRENT_TIMESTAMP AS created_at
FROM {{ ref('stg_customers') }}
WHERE ip_address IS NOT NULL
  AND ip_address != ''
