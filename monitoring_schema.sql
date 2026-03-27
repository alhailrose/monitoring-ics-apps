--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_check_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.account_check_configs (
    id character varying(36) NOT NULL,
    account_id character varying(36) NOT NULL,
    check_name character varying(128) NOT NULL,
    config json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.accounts (
    id character varying(36) NOT NULL,
    customer_id character varying(36) NOT NULL,
    profile_name character varying(128) NOT NULL,
    account_id character varying(20),
    display_name character varying(256) NOT NULL,
    is_active boolean NOT NULL,
    config_extra json,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    region text,
    alarm_names json,
    auth_method character varying(16) DEFAULT 'profile'::character varying NOT NULL,
    aws_access_key_id character varying(256),
    aws_secret_access_key_enc text,
    role_arn character varying(512),
    external_id character varying(256)
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: check_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.check_results (
    id character varying(36) NOT NULL,
    check_run_id character varying(36) NOT NULL,
    account_id character varying(36) NOT NULL,
    check_name character varying(128) NOT NULL,
    status character varying(32) NOT NULL,
    summary text,
    output text,
    details json,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_check_results_status_valid CHECK (((status)::text = ANY ((ARRAY['OK'::character varying, 'WARN'::character varying, 'ERROR'::character varying, 'ALARM'::character varying, 'NO_DATA'::character varying])::text[])))
);


--
-- Name: check_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.check_runs (
    id character varying(36) NOT NULL,
    customer_id character varying(36) NOT NULL,
    check_mode character varying(32) NOT NULL,
    check_name character varying(128),
    requested_by character varying(64) NOT NULL,
    slack_sent boolean NOT NULL,
    execution_time_seconds double precision,
    created_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_check_runs_mode_valid CHECK (((check_mode)::text = ANY ((ARRAY['single'::character varying, 'all'::character varying, 'arbel'::character varying])::text[])))
);


--
-- Name: customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customers (
    id character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    display_name character varying(256) NOT NULL,
    checks json NOT NULL,
    slack_webhook_url text,
    slack_channel character varying(128),
    slack_enabled boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    sso_session character varying(128),
    report_mode character varying(32) DEFAULT 'summary'::character varying NOT NULL,
    label character varying(256)
);


--
-- Name: finding_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.finding_events (
    id character varying(36) NOT NULL,
    check_run_id character varying(36) NOT NULL,
    account_id character varying(36) NOT NULL,
    check_name character varying(128) NOT NULL,
    finding_key character varying(256) NOT NULL,
    severity character varying(32) NOT NULL,
    title character varying(512) NOT NULL,
    description text,
    raw_payload json,
    created_at timestamp with time zone NOT NULL,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    last_seen_at timestamp with time zone,
    resolved_at timestamp with time zone,
    CONSTRAINT ck_finding_events_severity_valid CHECK (((severity)::text = ANY ((ARRAY['INFO'::character varying, 'LOW'::character varying, 'MEDIUM'::character varying, 'HIGH'::character varying, 'CRITICAL'::character varying, 'ALARM'::character varying])::text[])))
);


--
-- Name: metric_samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.metric_samples (
    id character varying(36) NOT NULL,
    check_run_id character varying(36) NOT NULL,
    account_id character varying(36) NOT NULL,
    check_name character varying(128) NOT NULL,
    metric_name character varying(128) NOT NULL,
    metric_status character varying(32) NOT NULL,
    value_num double precision,
    unit character varying(64),
    resource_role character varying(128),
    resource_id character varying(256),
    resource_name character varying(256),
    service_type character varying(32),
    section_name character varying(256),
    raw_payload json,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id character varying(36) NOT NULL,
    username character varying(128) NOT NULL,
    hashed_password character varying(256) NOT NULL,
    role character varying(32) DEFAULT 'user'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_users_role_valid CHECK (((role)::text = ANY ((ARRAY['super_user'::character varying, 'user'::character varying])::text[])))
);


--
-- Name: account_check_configs account_check_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_check_configs
    ADD CONSTRAINT account_check_configs_pkey PRIMARY KEY (id);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: check_results check_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.check_results
    ADD CONSTRAINT check_results_pkey PRIMARY KEY (id);


--
-- Name: check_runs check_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.check_runs
    ADD CONSTRAINT check_runs_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: finding_events finding_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finding_events
    ADD CONSTRAINT finding_events_pkey PRIMARY KEY (id);


--
-- Name: metric_samples metric_samples_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_pkey PRIMARY KEY (id);


--
-- Name: account_check_configs uq_account_check_config; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_check_configs
    ADD CONSTRAINT uq_account_check_config UNIQUE (account_id, check_name);


--
-- Name: accounts uq_customer_profile; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT uq_customer_profile UNIQUE (customer_id, profile_name);


--
-- Name: users uq_users_username; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_username UNIQUE (username);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_account_check_config_account; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_account_check_config_account ON public.account_check_configs USING btree (account_id);


--
-- Name: idx_account_check_config_check; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_account_check_config_check ON public.account_check_configs USING btree (check_name);


--
-- Name: idx_check_results_account_check; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_check_results_account_check ON public.check_results USING btree (account_id, check_name, created_at);


--
-- Name: idx_check_runs_customer_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_check_runs_customer_created ON public.check_runs USING btree (customer_id, created_at);


--
-- Name: idx_finding_events_account_check; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_finding_events_account_check ON public.finding_events USING btree (account_id, check_name, created_at);


--
-- Name: idx_finding_events_account_check_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_finding_events_account_check_key ON public.finding_events USING btree (account_id, check_name, finding_key, status);


--
-- Name: idx_metric_samples_account_metric; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_metric_samples_account_metric ON public.metric_samples USING btree (account_id, metric_name, created_at);


--
-- Name: ix_account_check_configs_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_account_check_configs_account_id ON public.account_check_configs USING btree (account_id);


--
-- Name: ix_accounts_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_accounts_customer_id ON public.accounts USING btree (customer_id);


--
-- Name: ix_accounts_profile_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_accounts_profile_name ON public.accounts USING btree (profile_name);


--
-- Name: ix_check_results_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_check_results_account_id ON public.check_results USING btree (account_id);


--
-- Name: ix_check_results_check_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_check_results_check_name ON public.check_results USING btree (check_name);


--
-- Name: ix_check_results_check_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_check_results_check_run_id ON public.check_results USING btree (check_run_id);


--
-- Name: ix_check_runs_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_check_runs_customer_id ON public.check_runs USING btree (customer_id);


--
-- Name: ix_customers_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_customers_name ON public.customers USING btree (name);


--
-- Name: ix_finding_events_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_finding_events_account_id ON public.finding_events USING btree (account_id);


--
-- Name: ix_finding_events_check_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_finding_events_check_name ON public.finding_events USING btree (check_name);


--
-- Name: ix_finding_events_check_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_finding_events_check_run_id ON public.finding_events USING btree (check_run_id);


--
-- Name: ix_metric_samples_account_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_account_id ON public.metric_samples USING btree (account_id);


--
-- Name: ix_metric_samples_check_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_check_name ON public.metric_samples USING btree (check_name);


--
-- Name: ix_metric_samples_check_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_check_run_id ON public.metric_samples USING btree (check_run_id);


--
-- Name: ix_metric_samples_metric_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_metric_samples_metric_name ON public.metric_samples USING btree (metric_name);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: account_check_configs account_check_configs_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account_check_configs
    ADD CONSTRAINT account_check_configs_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: accounts accounts_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: check_results check_results_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.check_results
    ADD CONSTRAINT check_results_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: check_results check_results_check_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.check_results
    ADD CONSTRAINT check_results_check_run_id_fkey FOREIGN KEY (check_run_id) REFERENCES public.check_runs(id) ON DELETE CASCADE;


--
-- Name: check_runs check_runs_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.check_runs
    ADD CONSTRAINT check_runs_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: finding_events finding_events_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finding_events
    ADD CONSTRAINT finding_events_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: finding_events finding_events_check_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finding_events
    ADD CONSTRAINT finding_events_check_run_id_fkey FOREIGN KEY (check_run_id) REFERENCES public.check_runs(id) ON DELETE CASCADE;


--
-- Name: metric_samples metric_samples_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: metric_samples metric_samples_check_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_samples
    ADD CONSTRAINT metric_samples_check_run_id_fkey FOREIGN KEY (check_run_id) REFERENCES public.check_runs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


