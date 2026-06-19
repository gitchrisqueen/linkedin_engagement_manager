-- Add 'past_due' to subscription_status ENUM so we can represent payment-failed-but-retrying
ALTER TABLE users
    MODIFY COLUMN subscription_status
        ENUM('active', 'inactive', 'trial', 'cancelled', 'past_due') DEFAULT 'inactive';

-- Track when the current billing period ends (used by the daily sync task).
-- Guard against duplicate-column errors when this migration is replayed after a
-- partial application (first statement committed, second was rejected).
SET @_col_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'users'
      AND COLUMN_NAME  = 'subscription_current_period_end'
);
SET @_ddl = IF(
    @_col_exists = 0,
    'ALTER TABLE users ADD COLUMN subscription_current_period_end TIMESTAMP NULL AFTER stripe_subscription_id',
    'DO 0'
);
PREPARE _lem_v24 FROM @_ddl;
EXECUTE _lem_v24;
DEALLOCATE PREPARE _lem_v24;
