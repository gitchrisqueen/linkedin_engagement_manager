-- Table for cookie management
CREATE TABLE IF NOT EXISTS cookies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    expiry TIMESTAMP NULL,
    secure BOOLEAN NOT NULL,
    http_only BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);