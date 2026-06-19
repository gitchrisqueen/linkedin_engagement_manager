-- Add 'past_due' to subscription_status ENUM so we can represent payment-failed-but-retrying
ALTER TABLE users
    MODIFY COLUMN subscription_status
        ENUM('active', 'inactive', 'trial', 'cancelled', 'past_due') DEFAULT 'inactive';

-- Track when the current billing period ends (used by the daily sync task)
ALTER TABLE users
    ADD COLUMN subscription_current_period_end TIMESTAMP NULL
        AFTER stripe_subscription_id;
