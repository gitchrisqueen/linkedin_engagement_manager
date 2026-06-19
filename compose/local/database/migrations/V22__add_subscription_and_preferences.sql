-- Subscription tracking
ALTER TABLE users
    ADD COLUMN subscription_tier ENUM('free_trial', 'starter', 'professional', 'enterprise') NULL AFTER subscription_status,
    ADD COLUMN trial_started_at TIMESTAMP NULL AFTER subscription_tier,
    ADD COLUMN trial_ends_at   TIMESTAMP NULL AFTER trial_started_at,
    ADD COLUMN stripe_customer_id      VARCHAR(255) NULL UNIQUE AFTER trial_ends_at,
    ADD COLUMN stripe_subscription_id  VARCHAR(255) NULL AFTER stripe_customer_id;

-- LinkedIn connection state (derived + stored for fast queries)
ALTER TABLE users
    ADD COLUMN linkedin_connection_status ENUM('connected', 'expired', 'disconnected') NOT NULL DEFAULT 'disconnected' AFTER stripe_subscription_id;

-- User preferences
ALTER TABLE users
    ADD COLUMN last_login_inactivate_delay INT NULL DEFAULT 90 AFTER linkedin_connection_status,
    ADD COLUMN auto_schedule_posts TINYINT(1) NOT NULL DEFAULT 1 AFTER last_login_inactivate_delay;

-- Migrate existing connected users: give them an active trial starting now
UPDATE users
SET subscription_status    = 'trial',
    subscription_tier      = 'free_trial',
    trial_started_at       = NOW(),
    trial_ends_at          = NOW() + INTERVAL 14 DAY,
    linkedin_connection_status = 'connected'
WHERE access_token IS NOT NULL
  AND subscription_status = 'inactive';
