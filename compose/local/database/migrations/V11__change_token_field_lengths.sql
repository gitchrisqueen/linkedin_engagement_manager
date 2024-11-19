-- Change access_token field to 512 in the users table
ALTER TABLE users CHANGE COLUMN access_token access_token VARCHAR(512) NULL;

-- Change refresh_token field to 512 in the users table
ALTER TABLE users CHANGE COLUMN refresh_token refresh_token VARCHAR(512) NULL;