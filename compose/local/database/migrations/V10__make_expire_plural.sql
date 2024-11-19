-- Change access_token_expire_in field to access_token_expires_in in the users table
ALTER TABLE users CHANGE COLUMN access_token_expire_in access_token_expires_in TIMESTAMP NULL;

-- Change refresh_token_expire_in field to refresh_token_expires_in in the users table
ALTER TABLE users CHANGE COLUMN refresh_token_expire_in refresh_token_expires_in TIMESTAMP NULL;
