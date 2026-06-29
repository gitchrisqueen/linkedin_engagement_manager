-- Per-user location for Selenium geo spoofing (city/country/locale) + capture source.
-- latitude/longitude (V18) and timezone (V28) already exist; these complete the set
-- so the browser's reported geolocation, timezone and locale match where the user
-- normally logs in, reducing LinkedIn "new location" login challenges.
ALTER TABLE users
  ADD COLUMN city            VARCHAR(120) NULL AFTER longitude,
  ADD COLUMN country         VARCHAR(2)   NULL AFTER city,
  ADD COLUMN locale          VARCHAR(10)  NULL AFTER country,
  ADD COLUMN location_source ENUM('manual', 'ip_autocapture') NULL AFTER locale;
