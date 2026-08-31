-- Migración local SQLite para Google Sign-In.
-- Conserva los usuarios actuales.

-- ==========================================================
-- Migración local SQLite para Google Sign-In
-- Conserva usuarios y relaciones existentes.
-- ==========================================================

PRAGMA foreign_keys = OFF;

-- Evita que SQLite cambie las referencias
-- de otras tablas de "users" a "users_old".
PRAGMA legacy_alter_table = ON;

BEGIN TRANSACTION;

-- 1. Renombrar temporalmente la tabla actual.
ALTER TABLE users RENAME TO users_old;

-- 2. Crear la nueva tabla con password nullable
--    y google_sub para Google OAuth.
CREATE TABLE users (
    id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password VARCHAR(255),
    is_verified BOOLEAN,
    verification_token VARCHAR(255),
    currency VARCHAR(10) NOT NULL,
    language VARCHAR(5) DEFAULT 'es',
    google_sub VARCHAR(255),
    PRIMARY KEY (id),
    UNIQUE (email),
    UNIQUE (google_sub)
);

-- 3. Copiar todos los usuarios existentes.
INSERT INTO users (
    id,
    name,
    email,
    password,
    is_verified,
    verification_token,
    currency,
    language
)
SELECT
    id,
    name,
    email,
    password,
    is_verified,
    verification_token,
    currency,
    language
FROM users_old;

-- 4. Eliminar tabla temporal.
DROP TABLE users_old;

COMMIT;

PRAGMA legacy_alter_table = OFF;
PRAGMA foreign_keys = ON;