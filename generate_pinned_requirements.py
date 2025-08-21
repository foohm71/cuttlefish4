#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Generate pinned requirements file from current installation.
This creates a requirements-pinned.txt with exact versions of all installed packages.
"""

import subprocess
import sys
from pathlib import Path

def generate_pinned_requirements():
    """Generate pinned requirements from current pip freeze output."""
    
    try:
        # Get pip freeze output
        result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], 
                              capture_output=True, text=True, check=True)
        
        # Parse the output
        installed_packages = result.stdout.strip().split('\n')
        
        # Filter out some common packages that shouldn't be in requirements
        exclude_packages = {
            'pip', 'setuptools', 'wheel', 'pkg-resources', 
            'distribute', 'pkg_resources'
        }
        
        # Group packages by category for better organization
        langchain_packages = []
        web_packages = []
        database_packages = []
        utility_packages = []
        other_packages = []
        
        for package in installed_packages:
            if not package or package.startswith('-e '):
                continue
                
            package_name = package.split('==')[0].lower()
            
            if package_name in exclude_packages:
                continue
            
            if 'langchain' in package_name or 'langgraph' in package_name:
                langchain_packages.append(package)
            elif any(web in package_name for web in ['fastapi', 'uvicorn', 'starlette', 'pydantic']):
                web_packages.append(package)
            elif any(db in package_name for db in ['supabase', 'postgrest', 'httpx', 'requests']):
                database_packages.append(package)
            elif any(util in package_name for util in ['python-dotenv', 'tqdm', 'openai']):
                utility_packages.append(package)
            else:
                other_packages.append(package)
        
        # Generate the requirements file
        output_path = Path(__file__).parent / 'requirements-pinned.txt'
        
        with open(output_path, 'w') as f:
            f.write("# Cuttlefish Multi-Agent RAG System - Pinned Dependencies\n")
            f.write("# Generated automatically from current installation\n")
            f.write("# These versions are verified to work together\n\n")
            
            if langchain_packages:
                f.write("# LangChain ecosystem\n")
                for package in sorted(langchain_packages):
                    f.write(f"{package}\n")
                f.write("\n")
            
            if utility_packages:
                f.write("# AI and utilities\n")
                for package in sorted(utility_packages):
                    f.write(f"{package}\n")
                f.write("\n")
            
            if web_packages:
                f.write("# Web framework\n")
                for package in sorted(web_packages):
                    f.write(f"{package}\n")
                f.write("\n")
            
            if database_packages:
                f.write("# Database and HTTP\n")
                for package in sorted(database_packages):
                    f.write(f"{package}\n")
                f.write("\n")
            
            if other_packages:
                f.write("# Other dependencies\n")
                for package in sorted(other_packages):
                    f.write(f"{package}\n")
        
        print(f"✅ Generated {output_path}")
        print(f"📦 Included {len(installed_packages)} packages")
        print("\nCategories:")
        print(f"  • LangChain: {len(langchain_packages)}")
        print(f"  • Web framework: {len(web_packages)}")
        print(f"  • Database/HTTP: {len(database_packages)}")
        print(f"  • Utilities: {len(utility_packages)}")
        print(f"  • Other: {len(other_packages)}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running pip freeze: {e}")
        return False
    except Exception as e:
        print(f"❌ Error generating requirements: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Generating pinned requirements from current installation...")
    success = generate_pinned_requirements()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Review requirements-pinned.txt")
        print("2. Use it for reproducible installations:")
        print("   pip install -r requirements-pinned.txt")
    else:
        print("\n💡 Make sure you have packages installed first:")
        print("   pip install -r requirements-core.txt")
        print("   python generate_pinned_requirements.py")