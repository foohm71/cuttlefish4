-- Cuttlefish4 Authentication Database Schema
-- SQLite database for user management and rate limiting

-- Users table - stores authenticated users and their access limits
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    google_id TEXT UNIQUE NOT NULL,
    display_name TEXT,
    profile_picture TEXT,
    daily_limit INTEGER DEFAULT 50,
    requests_used INTEGER DEFAULT 0,
    last_reset_date DATE DEFAULT CURRENT_DATE,
    unlimited_access BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API requests table - logs all API usage for analytics and auditing
CREATE TABLE IF NOT EXISTS api_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    query_text TEXT,
    user_can_wait BOOLEAN,
    production_incident BOOLEAN,
    processing_time REAL,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_last_reset_date ON users(last_reset_date);
CREATE INDEX IF NOT EXISTS idx_api_requests_user_email ON api_requests(user_email);
CREATE INDEX IF NOT EXISTS idx_api_requests_timestamp ON api_requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_requests_endpoint ON api_requests(endpoint);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_users_updated_at 
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE email = NEW.email;
END;

-- Insert default admin user
INSERT OR IGNORE INTO users (
    email, 
    google_id, 
    display_name, 
    unlimited_access, 
    is_admin, 
    daily_limit
) VALUES (
    'foohm71@gmail.com', 
    'temp_foohm71_google_id', 
    'Admin User', 
    TRUE, 
    TRUE, 
    999999
);