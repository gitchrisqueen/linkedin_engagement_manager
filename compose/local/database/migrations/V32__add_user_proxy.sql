-- Per-user egress proxy for Selenium automation.
-- LinkedIn flags logins whose IP geolocates far from where the user normally signs in.
-- Routing a user's browser session through a proxy near their location (e.g. a free
-- home exit node they provide) makes the login look normal. Stored as a full proxy URL
-- (scheme://[user:pass@]host:port); NULL = no proxy (egress straight from the host).
ALTER TABLE users
    ADD COLUMN proxy_url VARCHAR(500) NULL AFTER country;
