-- Create a profiles table id, profile_url, email, data (json string of data), and updated_at timestamp.
-- Also create a unique index on the profile_url column.
CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    profile_url VARCHAR(255) ,
    email VARCHAR(255) ,
    data JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (profile_url),
    UNIQUE (email)
);