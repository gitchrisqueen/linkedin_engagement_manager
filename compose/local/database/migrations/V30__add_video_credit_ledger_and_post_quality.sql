-- Premium video credits: a ledger (balance = SUM(delta)) mirroring avatar_credit_ledger,
-- plus a per-post chosen video quality tier.
CREATE TABLE IF NOT EXISTS video_credit_ledger (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT          NOT NULL,
    delta             INT          NOT NULL,  -- positive for purchases/refunds, negative for premium renders
    reason            VARCHAR(128) NOT NULL,  -- e.g. "purchase_pack_15", "premium_video", "premium_video_refund"
    stripe_session_id VARCHAR(255) NULL,      -- for idempotent webhook processing
    post_id           INT          NULL,      -- links a debit/refund to the post it rendered
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Desired video quality tier for a post: 'standard' (free), 'premium' (veo3.1_fast, 1 credit),
-- or 'premium_top' (veo3.1, 3 credits).
ALTER TABLE posts ADD COLUMN video_quality VARCHAR(32) NOT NULL DEFAULT 'standard';
