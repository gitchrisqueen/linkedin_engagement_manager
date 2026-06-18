-- Add last_login timestamp for active user detection (Issue #29)
ALTER TABLE users
ADD COLUMN last_login TIMESTAMP NULL AFTER company_linked_in_url;

-- Add subscription_status for active user detection (Issue #29)
ALTER TABLE users
ADD COLUMN subscription_status ENUM('active', 'inactive', 'trial', 'cancelled') DEFAULT 'inactive' AFTER last_login;

-- Add geolocation fields for Selenium browser spoofing (Issue #30)
ALTER TABLE users
ADD COLUMN latitude DECIMAL(10, 7) NULL AFTER subscription_status,
ADD COLUMN longitude DECIMAL(10, 7) NULL AFTER latitude;
