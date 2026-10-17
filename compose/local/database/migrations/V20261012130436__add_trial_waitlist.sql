-- Issue #2377: the P0 trial cohort cap's join-the-list form.
--
-- While LAUNCH_PHASE=P0 only P0_TRIAL_COHORT_CAP self-serve trial accounts are created. A signup past
-- that cap is offered a form that takes an email address and nothing else; this table is where that
-- address lands. Nothing is sent to it: the row is a list for the owner to read, not a queue.
--
-- One row per address (the UNIQUE key): joining twice is a no-op, not a second row. launch_phase
-- records which phase was live when the address joined, so a list carried into P1 can still be read
-- as "these asked during P0".
CREATE TABLE IF NOT EXISTS trial_waitlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    launch_phase VARCHAR(8) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_trial_waitlist_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
