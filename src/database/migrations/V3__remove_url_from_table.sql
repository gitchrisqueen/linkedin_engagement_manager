-- Update the cookies table so it no longer uses the url column
-- Add an index containing the domain and name so that only unique entries are added
ALTER TABLE cookies
DROP COLUMN url,
ADD UNIQUE INDEX domain_name_unique (domain, name);