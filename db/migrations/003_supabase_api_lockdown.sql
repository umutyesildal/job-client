-- The application uses server-side PostgreSQL connections, not Supabase's
-- browser Data API. Keep all public-schema objects private from API roles.
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format('REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM %I', api_role);
            EXECUTE format('REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM %I', api_role);
            EXECUTE format('REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM %I', api_role);
            EXECUTE format('REVOKE USAGE ON SCHEMA public FROM %I', api_role);
        END IF;
    END LOOP;
END
$$;
