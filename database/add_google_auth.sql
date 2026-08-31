-- ==========================================================
-- Migration: Add Google authentication support
-- Database: PostgreSQL / Supabase
-- Table: public.users
-- ==========================================================

-- Store Google's unique OpenID Connect identifier ("sub").
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255);

-- Prevent the same Google account from being linked
-- to more than one application user.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub
ON public.users (google_sub);