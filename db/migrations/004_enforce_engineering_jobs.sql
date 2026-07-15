-- Canonical storage contains only jobs accepted by the engineering taxonomy.
-- Fingerprints intentionally remain so removed rows cannot reappear as new.
DELETE FROM jobs
WHERE btrim(role) = '';

ALTER TABLE jobs
    DROP CONSTRAINT IF EXISTS jobs_role_not_blank;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_role_not_blank CHECK (btrim(role) <> '');
