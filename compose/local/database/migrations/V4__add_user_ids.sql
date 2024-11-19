-- Create a users table with email and password and updated_at timestamp and unique email key
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_email (email)
);

-- ADD foreign key to posts table
ALTER TABLE posts
ADD COLUMN user_id INT,
ADD CONSTRAINT fk_posts_user_id FOREIGN KEY (user_id) REFERENCES users(id);

-- ADD field for user_id and foreign key to cookies table.
-- Update the domain_name_unique key to include the user_id column
ALTER TABLE cookies
ADD COLUMN user_id INT,
ADD CONSTRAINT fk_cookies_user_id FOREIGN KEY (user_id) REFERENCES users(id),
DROP INDEX domain_name_unique,
ADD UNIQUE KEY domain_name_unique (domain, name, user_id);