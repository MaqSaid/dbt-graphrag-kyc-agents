-- Graph node: Address entities (deduplicated by hash)
SELECT DISTINCT
    address_hash AS entity_id,
    address_hash,
    address AS full_address,
    CURRENT_TIMESTAMP AS created_at
FROM {{ ref('stg_customers') }}
WHERE address IS NOT NULL
  AND address != ''
