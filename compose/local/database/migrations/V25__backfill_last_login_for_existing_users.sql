-- Backfill last_login for existing users who connected LinkedIn before the
-- session-based auth system was introduced. Without this, get_active_user_ids
-- excludes all pre-migration users from automation because last_login IS NULL.
UPDATE users
SET last_login = NOW()
WHERE last_login IS NULL
  AND access_token IS NOT NULL
  AND linkedin_connection_status = 'connected';
