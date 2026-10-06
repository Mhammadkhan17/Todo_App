-- Database initialization script for Todo Application
-- This script runs when PostgreSQL container starts for the first time

-- Create extensions if they don't exist (for advanced PostgreSQL features)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create initial user for development/testing purposes
-- The table name and column names must match the SQLModel schema
INSERT INTO users (email, username, password_hash, full_name, is_active, created_at, updated_at, email_verified)
VALUES
    ('admin@example.com', 'admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Admin User', true, NOW(), NOW(), true),
    ('test@example.com', 'testuser', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Test User', true, NOW(), NOW(), true)
ON CONFLICT (email) DO NOTHING;

-- Insert sample tasks for the users (only after users exist)
-- Using the correct table name and column names from SQLModel schema
WITH user_ids AS (
    SELECT id, email FROM users
)
INSERT INTO tasks (title, description, priority, due_date, status, created_at, updated_at, user_id)
SELECT
    'Sample Task 1',
    'This is a sample task for testing purposes',
    'MEDIUM',
    CURRENT_DATE + INTERVAL '7 days',
    'ACTIVE',
    NOW(),
    NOW(),
    u.id
FROM user_ids u
WHERE u.email = 'admin@example.com'
ON CONFLICT DO NOTHING;

WITH user_ids AS (
    SELECT id, email FROM users
)
INSERT INTO tasks (title, description, priority, due_date, status, created_at, updated_at, user_id)
SELECT
    'Sample Task 2',
    'Another sample task for testing',
    'HIGH',
    CURRENT_DATE + INTERVAL '3 days',
    'ACTIVE',
    NOW(),
    NOW(),
    u.id
FROM user_ids u
WHERE u.email = 'admin@example.com'
ON CONFLICT DO NOTHING;

WITH user_ids AS (
    SELECT id, email FROM users
)
INSERT INTO tasks (title, description, priority, due_date, status, created_at, updated_at, user_id)
SELECT
    'Completed Sample Task',
    'This is a completed sample task',
    'LOW',
    CURRENT_DATE - INTERVAL '2 days',
    'COMPLETED',
    NOW() - INTERVAL '3 days',
    NOW(),
    u.id
FROM user_ids u
WHERE u.email = 'test@example.com'
ON CONFLICT DO NOTHING;