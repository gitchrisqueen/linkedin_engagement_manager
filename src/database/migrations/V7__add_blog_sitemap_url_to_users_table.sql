-- Add fields for blog url and sitemap url to the users table
ALTER TABLE users ADD COLUMN blog_url VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN sitemap_url VARCHAR(255) NULL;
