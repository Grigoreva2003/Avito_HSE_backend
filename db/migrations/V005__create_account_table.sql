-- Migration: V005 - Account table for JWT authorization

CREATE TABLE account (
    id SERIAL PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_account_login ON account(login);

COMMENT ON TABLE account IS 'Service accounts used for JWT authentication';
