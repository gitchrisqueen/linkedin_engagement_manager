-- Throttle for LinkedIn session notification emails (connect / re-validate). We email a
-- user when they have no validated session cookie, or when a stored one stops working —
-- but only at most once per window, tracked here.
ALTER TABLE users
    ADD COLUMN linkedin_session_email_sent_at DATETIME NULL AFTER proxy_url;
