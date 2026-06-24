-- Recreate every user_id foreign key with ON DELETE CASCADE so that
-- removing a user automatically cleans up all their data without
-- requiring manual deletion of child rows first.
--
-- Each FK is dropped and re-added in separate ALTER TABLE statements because
-- MySQL/MariaDB does not allow DROP and ADD of the same constraint name in a
-- single ALTER TABLE statement.

-- cookies
ALTER TABLE cookies DROP FOREIGN KEY fk_cookies_user_id;
ALTER TABLE cookies ADD CONSTRAINT fk_cookies_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- profiles
ALTER TABLE profiles DROP FOREIGN KEY fk_profiles_user_id;
ALTER TABLE profiles ADD CONSTRAINT fk_profiles_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- sessions
ALTER TABLE sessions DROP FOREIGN KEY sessions_ibfk_1;
ALTER TABLE sessions ADD CONSTRAINT sessions_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- avatar_credit_ledger
ALTER TABLE avatar_credit_ledger DROP FOREIGN KEY avatar_credit_ledger_ibfk_1;
ALTER TABLE avatar_credit_ledger ADD CONSTRAINT avatar_credit_ledger_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- avatar_trainings
ALTER TABLE avatar_trainings DROP FOREIGN KEY avatar_trainings_ibfk_1;
ALTER TABLE avatar_trainings ADD CONSTRAINT avatar_trainings_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- logs has two FKs: user_id -> users and post_id -> posts.
-- Recreate both with CASCADE so logs are cleaned up when either parent is deleted.
ALTER TABLE logs DROP FOREIGN KEY fk_logs_user_id;
ALTER TABLE logs DROP FOREIGN KEY logs_ibfk_1;
ALTER TABLE logs ADD CONSTRAINT fk_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE logs ADD CONSTRAINT logs_ibfk_1 FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;

-- approvals reference posts; cascade so approval rows are removed when the post is.
ALTER TABLE approvals DROP FOREIGN KEY approvals_ibfk_1;
ALTER TABLE approvals ADD CONSTRAINT approvals_ibfk_1 FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE;

-- posts must be altered last because other tables reference it.
ALTER TABLE posts DROP FOREIGN KEY fk_posts_user_id;
ALTER TABLE posts ADD CONSTRAINT fk_posts_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Remove inactive placeholder accounts that were used for testing.
-- CASCADE propagates the deletes through posts, cookies, logs, profiles,
-- sessions, approvals, avatar_credit_ledger, and avatar_trainings automatically.
DELETE FROM users WHERE id IN (1, 70);
