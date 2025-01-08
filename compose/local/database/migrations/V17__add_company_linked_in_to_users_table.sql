-- Add company linked url to users table
ALTER TABLE users
ADD COLUMN company_linked_in_url VARCHAR(255) NULL AFTER sitemap_url;
