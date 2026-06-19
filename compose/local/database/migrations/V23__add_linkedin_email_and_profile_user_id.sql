-- Store the LinkedIn account's primary email (from /userinfo) separately from the app login email.
-- This lets Selenium automation use the correct LinkedIn credential even when the two emails differ.
ALTER TABLE users ADD COLUMN linkedin_email VARCHAR(255) NULL AFTER email;

-- Key the "own profile" cache by user_id instead of email so it survives email changes.
ALTER TABLE profiles ADD COLUMN user_id INT NULL AFTER id;
ALTER TABLE profiles ADD CONSTRAINT fk_profiles_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE profiles ADD UNIQUE KEY uniq_profiles_user_id (user_id);
