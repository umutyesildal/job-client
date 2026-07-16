DO $$
BEGIN
    CREATE ROLE daily_jobs_web NOLOGIN;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO daily_jobs_web', current_database());
END
$$;
GRANT USAGE ON SCHEMA public TO daily_jobs_web;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM daily_jobs_web;
GRANT SELECT ON public_jobs, daily_jobs, data_status TO daily_jobs_web;
