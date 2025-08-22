#!/usr/bin/env python3
"""
Network diagnostic script for Render->Supabase connectivity.
This can be run as a one-off job in Render to test connectivity.
"""

import socket
import subprocess
import sys
import os

def test_dns_resolution():
    """Test DNS resolution for Supabase host."""
    host = "db.jzstozvrjjhmwigycjtj.supabase.co"
    print(f"🔍 Testing DNS resolution for {host}")
    
    try:
        import socket
        ip = socket.gethostbyname(host)
        print(f"✅ DNS Resolution: {host} -> {ip}")
        return ip
    except Exception as e:
        print(f"❌ DNS Resolution failed: {e}")
        return None

def test_ping(host):
    """Test basic connectivity with ping."""
    print(f"\n🏓 Testing ping to {host}")
    try:
        result = subprocess.run(['ping', '-c', '3', host], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Ping successful")
            print(result.stdout[-200:])  # Last 200 chars
        else:
            print("❌ Ping failed")
            print(result.stderr[-200:])
    except Exception as e:
        print(f"❌ Ping error: {e}")

def test_port_connectivity(host, port):
    """Test specific port connectivity."""
    print(f"\n🔌 Testing TCP connection to {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} is reachable")
            return True
        else:
            print(f"❌ Port {port} is not reachable (error: {result})")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_alternative_ports():
    """Test alternative Supabase connection methods."""
    host = "db.jzstozvrjjhmwigycjtj.supabase.co"
    ports_to_test = [
        (5432, "Direct PostgreSQL"),
        (6543, "Connection Pooling"),
        (5433, "Alternative PostgreSQL")
    ]
    
    print(f"\n🔄 Testing multiple connection ports...")
    working_ports = []
    
    for port, description in ports_to_test:
        print(f"\nTesting {description} (port {port}):")
        if test_port_connectivity(host, port):
            working_ports.append((port, description))
    
    return working_ports

def test_traceroute(host):
    """Test network path to destination."""
    print(f"\n🛣️  Testing route to {host}")
    try:
        # Try traceroute (Linux) or tracert (Windows)
        cmd = ['traceroute', '-n', '-m', '10', host]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print("Network path:")
                print(result.stdout[-500:])  # Last 500 chars
            else:
                print("❌ Traceroute failed")
        except FileNotFoundError:
            # Try with tracert on Windows or systems without traceroute
            print("Traceroute not available, trying alternative methods...")
    except Exception as e:
        print(f"Route test error: {e}")

def check_environment():
    """Check environment and network configuration."""
    print("\n🌍 Environment Information:")
    print(f"Python version: {sys.version}")
    
    # Check if we're in a container
    try:
        with open('/proc/1/cgroup', 'r') as f:
            cgroup_info = f.read()
            if 'docker' in cgroup_info or 'container' in cgroup_info:
                print("✅ Running in container environment")
            else:
                print("ℹ️  Not in container environment")
    except:
        print("ℹ️  Cannot determine container status")
    
    # Check network interfaces
    try:
        result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("Network interfaces:")
            print(result.stdout[-300:])
    except:
        print("Cannot check network interfaces")

def main():
    print("🚀 Render->Supabase Network Diagnostic")
    print("=" * 50)
    
    host = "db.jzstozvrjjhmwigycjtj.supabase.co"
    
    # Step 1: Environment check
    check_environment()
    
    # Step 2: DNS Resolution
    ip = test_dns_resolution()
    
    # Step 3: Basic connectivity
    if ip:
        test_ping(ip)
    
    # Step 4: Port connectivity tests
    working_ports = test_alternative_ports()
    
    # Step 5: Network path analysis
    test_traceroute(host)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    if working_ports:
        print("✅ GOOD NEWS: Some ports are working!")
        for port, desc in working_ports:
            print(f"   Port {port}: {desc}")
        print(f"\n💡 Try using port {working_ports[0][0]} in your DATABASE_URL:")
        print(f"   postgresql://postgres:PASSWORD@{host}:{working_ports[0][0]}/postgres")
    else:
        print("❌ NO PORTS WORKING: This is a network connectivity issue")
        print("\n🔍 Possible causes:")
        print("   1. Render's outbound network restrictions")
        print("   2. Supabase firewall blocking Render's IP ranges")
        print("   3. Regional network routing issues")
        print("\n💡 Solutions to try:")
        print("   1. Contact Render support about Supabase connectivity")
        print("   2. Try a different Render region")
        print("   3. Check Supabase's network access settings")

if __name__ == "__main__":
    main()