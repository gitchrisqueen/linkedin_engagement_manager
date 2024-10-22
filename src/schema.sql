CREATE DATABASE IF NOT EXISTS linkedin_manager;

USE linkedin_manager;

-- Table to store generated posts (carousel, text, video)
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_type ENUM('carousel', 'text', 'video') NOT NULL,
    content TEXT NOT NULL,
    status ENUM('pending', 'approved', 'rejected', 'scheduled', 'posted') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP NULL
);

-- Table to log actions (comments, DMs, replies)
CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type ENUM('comment', 'dm', 'reply', 'post') NOT NULL,
    post_id INT NULL,
    message TEXT NOT NULL,
    result ENUM('success', 'failure') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- Table for approval management
CREATE TABLE IF NOT EXISTS approvals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    reviewed_at TIMESTAMP NULL,
    reviewer VARCHAR(255) NULL,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);
