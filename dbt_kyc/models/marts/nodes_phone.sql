-- Graph node: Phone Number entities
SELECT DISTINCT
    md5(phone) AS entity_id,
    phone AS phone_number,
    CURRENT_TIMESTAMP AS created_at
FROM {{ ref('stg_customers') }}
WHERE phone IS NOT NULL
  AND phone != ''
