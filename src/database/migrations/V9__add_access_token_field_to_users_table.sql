-- Add an access_token field to the users table and allow Null
ALTER TABLE users ADD COLUMN access_token VARCHAR(255) NULL;

-- Add access_token_expire_at field to users table and allow Null
ALTER TABLE users ADD COLUMN access_token_expire_in TIMESTAMP NULL;

-- Add a refresh_token field to the users table and allow Null
ALTER TABLE users ADD COLUMN refresh_token VARCHAR(255) NULL;

-- Add refresh_token_expire_at field to users table and allow Null
ALTER TABLE users ADD COLUMN refresh_token_expire_in TIMESTAMP NULL;

-- Allow the password field in the users table to be nullable
ALTER TABLE users MODIFY COLUMN password VARCHAR(255) NULL;