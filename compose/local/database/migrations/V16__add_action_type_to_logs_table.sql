-- Add to the logs table action_type field enum options
ALTER TABLE logs
MODIFY COLUMN action_type ENUM('comment','dm','reply','post','engaged') NOT NULL;
