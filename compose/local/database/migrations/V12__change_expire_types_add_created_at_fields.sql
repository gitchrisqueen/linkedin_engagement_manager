-- Change the access_token_expires_in field  to int
ALTER TABLE users CHANGE COLUMN access_token_expires_in access_token_expires_in INT NULL;

-- Add access_token_created_at field in users table with default null and allow nullable
ALTER TABLE users ADD COLUMN access_token_created_at TIMESTAMP NULL DEFAULT NULL;

-- Change the refresh_token_expires_in field to int
ALTER TABLE users CHANGE COLUMN refresh_token_expires_in refresh_token_expires_in INT NULL;

-- Add refresh_token_created_at field in users table with default null and allow nullable
ALTER TABLE users ADD COLUMN refresh_token_created_at TIMESTAMP NULL DEFAULT NULL;