CREATE TABLE IF NOT EXISTS email_pin_auth (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    pin         CHAR(64) NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    used        TINYINT(1) DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email_pin (email, pin),
    INDEX idx_expires (expires_at)
);
