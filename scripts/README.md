# User Management Scripts

This directory contains scripts for managing Cuttlefish4 users and access control.

## Scripts Overview

### 1. `manage_users.py` - Full User Management CLI

Comprehensive user management with all options:

```bash
# List all users
python scripts/manage_users.py list

# Add new user
python scripts/manage_users.py add user@example.com --limit 200 --admin --unlimited

# Update user settings
python scripts/manage_users.py update user@example.com --limit 500 --unlimited

# Remove user
python scripts/manage_users.py remove user@example.com

# Reset usage counters
python scripts/manage_users.py reset-usage --email user@example.com

# System statistics
python scripts/manage_users.py stats
```

### 2. `quick_user_setup.py` - Quick Setup Commands

Simplified commands for common operations:

```bash
# Setup admin user with unlimited access
python scripts/quick_user_setup.py setup-admin foohm71@gmail.com

# Setup premium user with high limit
python scripts/quick_user_setup.py setup-premium user@company.com 1000

# Setup standard user
python scripts/quick_user_setup.py setup-standard user@example.com 100

# Grant unlimited access
python scripts/quick_user_setup.py grant-unlimited trusted@example.com

# Revoke unlimited access
python scripts/quick_user_setup.py revoke-unlimited user@example.com 200

# Admin privileges
python scripts/quick_user_setup.py make-admin user@example.com
python scripts/quick_user_setup.py remove-admin user@example.com

# Account status
python scripts/quick_user_setup.py activate user@example.com
python scripts/quick_user_setup.py deactivate user@example.com

# List users
python scripts/quick_user_setup.py list
```

## User Setup Examples

### Admin User (foohm71@gmail.com already configured)
```bash
python scripts/quick_user_setup.py setup-admin foohm71@gmail.com
```

### Company Users
```bash
# Premium developer
python scripts/quick_user_setup.py setup-premium dev@company.com 500

# Standard user
python scripts/quick_user_setup.py setup-standard user@company.com 100

# Unlimited trusted user
python scripts/quick_user_setup.py setup-admin trusted@company.com
```

### Modify Existing Users
```bash
# Increase someone's limit
python scripts/manage_users.py update user@example.com --limit 300

# Grant unlimited access
python scripts/quick_user_setup.py grant-unlimited user@example.com

# Make someone admin
python scripts/quick_user_setup.py make-admin user@example.com

# Deactivate problematic user
python scripts/quick_user_setup.py deactivate spam@example.com
```

## Database Location

By default, the database is stored at `./users.db`. You can override this with the `DATABASE_PATH` environment variable:

```bash
export DATABASE_PATH="/path/to/your/database.db"
python scripts/manage_users.py list
```

## Usage Monitoring

```bash
# View system statistics
python scripts/manage_users.py stats

# Reset all users' daily usage
python scripts/manage_users.py reset-usage

# Reset specific user's usage
python scripts/manage_users.py reset-usage --email user@example.com
```

## Notes

- **foohm71@gmail.com** is pre-configured as an admin with unlimited access
- Users are automatically created when they first sign in with Google
- Daily usage counters reset automatically at midnight
- Admin users can manage other users through the API endpoints
- All operations are logged for auditing purposes