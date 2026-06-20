-- Avatar training jobs: one row per Replicate LoRA fine-tune started by a user
CREATE TABLE IF NOT EXISTS avatar_trainings (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    training_id  VARCHAR(255) NOT NULL,
    model_ref    VARCHAR(512)    NULL,
    trigger_word VARCHAR(64)  NOT NULL,
    status       ENUM('starting','processing','succeeded','failed','canceled') NOT NULL DEFAULT 'starting',
    is_active    TINYINT(1)   NOT NULL DEFAULT 0,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
