-- Credit ledger: one row per credit transaction (purchase, spend, refund)
-- Balance is derived as SUM(delta) for a user — supports full audit history.
CREATE TABLE IF NOT EXISTS avatar_credit_ledger (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT          NOT NULL,
    delta             INT          NOT NULL,
    reason            VARCHAR(128) NOT NULL,
    stripe_session_id VARCHAR(255) NULL,
    training_id       VARCHAR(255) NULL,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
