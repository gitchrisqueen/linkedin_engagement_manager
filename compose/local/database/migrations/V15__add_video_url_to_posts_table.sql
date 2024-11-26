-- Add video_url field to posts table after the content field
ALTER TABLE posts ADD COLUMN video_url TEXT NULL AFTER content;
