#!/usr/bin/env python3
"""
Quick user setup script for common operations.
Provides shortcuts for frequently used user management tasks.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from manage_users import add_user, update_user, list_users

def setup_admin_user(email: str):
    """Set up a user with admin and unlimited access."""
    print(f"Setting up admin user: {email}")
    add_user(
        email=email,
        unlimited=True,
        admin=True,
        daily_limit=999999,
        name="Admin User"
    )

def setup_premium_user(email: str, limit: int = 1000):
    """Set up a user with high daily limit."""
    print(f"Setting up premium user: {email} (limit: {limit})")
    add_user(
        email=email,
        unlimited=False,
        admin=False,
        daily_limit=limit
    )

def setup_standard_user(email: str, limit: int = 50):
    """Set up a standard user."""
    print(f"Setting up standard user: {email} (limit: {limit})")
    add_user(
        email=email,
        unlimited=False,
        admin=False,
        daily_limit=limit
    )

def grant_unlimited(email: str):
    """Grant unlimited access to existing user."""
    print(f"Granting unlimited access to: {email}")
    update_user(email=email, unlimited=True)

def revoke_unlimited(email: str, new_limit: int = 50):
    """Revoke unlimited access and set daily limit."""
    print(f"Revoking unlimited access for: {email} (new limit: {new_limit})")
    update_user(email=email, unlimited=False, daily_limit=new_limit)

def make_admin(email: str):
    """Give admin privileges to user."""
    print(f"Granting admin privileges to: {email}")
    update_user(email=email, admin=True)

def remove_admin(email: str):
    """Remove admin privileges from user."""
    print(f"Removing admin privileges from: {email}")
    update_user(email=email, admin=False)

def deactivate_user(email: str):
    """Deactivate a user account."""
    print(f"Deactivating user: {email}")
    update_user(email=email, active=False)

def activate_user(email: str):
    """Activate a user account."""
    print(f"Activating user: {email}")
    update_user(email=email, active=True)

def main():
    if len(sys.argv) < 2:
        print("Quick User Setup Commands:")
        print("")
        print("Setup Users:")
        print("  python quick_user_setup.py setup-admin <email>")
        print("  python quick_user_setup.py setup-premium <email> [limit]")
        print("  python quick_user_setup.py setup-standard <email> [limit]")
        print("")
        print("Modify Access:")
        print("  python quick_user_setup.py grant-unlimited <email>")
        print("  python quick_user_setup.py revoke-unlimited <email> [new_limit]")
        print("  python quick_user_setup.py make-admin <email>")
        print("  python quick_user_setup.py remove-admin <email>")
        print("")
        print("Account Status:")
        print("  python quick_user_setup.py activate <email>")
        print("  python quick_user_setup.py deactivate <email>")
        print("  python quick_user_setup.py list")
        print("")
        print("Examples:")
        print("  python quick_user_setup.py setup-admin foohm71@gmail.com")
        print("  python quick_user_setup.py setup-premium user@company.com 500")
        print("  python quick_user_setup.py grant-unlimited trusted@company.com")
        return
    
    command = sys.argv[1]
    
    if command == 'setup-admin' and len(sys.argv) >= 3:
        setup_admin_user(sys.argv[2])
    
    elif command == 'setup-premium' and len(sys.argv) >= 3:
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
        setup_premium_user(sys.argv[2], limit)
    
    elif command == 'setup-standard' and len(sys.argv) >= 3:
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        setup_standard_user(sys.argv[2], limit)
    
    elif command == 'grant-unlimited' and len(sys.argv) >= 3:
        grant_unlimited(sys.argv[2])
    
    elif command == 'revoke-unlimited' and len(sys.argv) >= 3:
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        revoke_unlimited(sys.argv[2], limit)
    
    elif command == 'make-admin' and len(sys.argv) >= 3:
        make_admin(sys.argv[2])
    
    elif command == 'remove-admin' and len(sys.argv) >= 3:
        remove_admin(sys.argv[2])
    
    elif command == 'activate' and len(sys.argv) >= 3:
        activate_user(sys.argv[2])
    
    elif command == 'deactivate' and len(sys.argv) >= 3:
        deactivate_user(sys.argv[2])
    
    elif command == 'list':
        list_users()
    
    else:
        print(f"❌ Unknown command or missing arguments: {command}")
        print("Run without arguments to see usage help.")

if __name__ == "__main__":
    main()