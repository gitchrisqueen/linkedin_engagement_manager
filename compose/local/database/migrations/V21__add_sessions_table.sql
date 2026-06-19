CREATE TABLE IF NOT EXISTS sessions (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    session_token VARCHAR(64) NOT NULL UNIQUE,
    user_id       INT NOT NULL,
    expires_at    TIMESTAMP NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token (session_token),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
