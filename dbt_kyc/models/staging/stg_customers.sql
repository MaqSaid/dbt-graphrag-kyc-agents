-- Staging model: clean and deduplicate raw customer records
SELECT DISTINCT
    customer_id,
    TRIM(full_name) AS full_name,
    date_of_birth,
    national_id,
    TRIM(address) AS address,
    LOWER(TRIM(email)) AS email,
    phone,
    ip_address,
    md5(LOWER(TRIM(address))) AS address_hash,
    CURRENT_TIMESTAMP AS loaded_at
FROM {{ source('raw', 'customers') }}
WHERE customer_id IS NOT NULL
  AND full_name IS NOT NULL
