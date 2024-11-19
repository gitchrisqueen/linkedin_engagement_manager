-- Add a planning status to the post table status field enum options
ALTER TABLE posts
MODIFY COLUMN status ENUM('planning','pending','approved','rejected','scheduled','posted') NOT NULL DEFAULT 'pending';

-- Add buyer_stage to the posts table
ALTER TABLE posts
ADD COLUMN buyer_stage ENUM('awareness', 'consideration', 'decision') NOT NULL DEFAULT 'awareness';