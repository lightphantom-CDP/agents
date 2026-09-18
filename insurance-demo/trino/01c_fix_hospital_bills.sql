-- Run ONLY this if ext_hospital_bills failed (Hue → Trino, hive.insurance_leo_trino)

DROP TABLE IF EXISTS hive.insurance_leo_trino.ext_hospital_bills;

CREATE TABLE hive.insurance_leo_trino.ext_hospital_bills (
    bill_line_id    VARCHAR,
    claim_id        VARCHAR,
    line_category   VARCHAR,
    description     VARCHAR,
    amount          VARCHAR,
    is_experimental VARCHAR
)
WITH (
    format = 'CSV',
    external_location = 's3a://lhdemocdpbca1/insurancedemo/raw/hospital_bills/',
    skip_header_line_count = 1
);
