-- Add user_id field to logs table with foreign key to users table
ALTER TABLE logs ADD COLUMN user_id INT NULL AFTER id;
ALTER TABLE logs ADD CONSTRAINT fk_logs_user_id FOREIGN KEY (user_id) REFERENCES users (id);

-- Allow Null for post_url and message
ALTER TABLE logs MODIFY COLUMN post_url TEXT NULL;
ALTER TABLE logs MODIFY COLUMN message TEXT NULL;