import socket
import subprocess
import platform
import requests

def get_local_ip():
    """Get the local IP address - most reliable method"""
    try:
        # Create a socket and connect to a remote address
        # This doesn't actually send data, just determines routing
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # Google's DNS
            local_ip = s.getsockname()[0]
            return local_ip
    except Exception as e:
        return f"Error: {e}"

def get_local_ip_hostname():
    """Alternative method using hostname"""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        return f"Error: {e}"

def get_all_local_ips():
    """Get all local IP addresses"""
    try:
        hostname = socket.gethostname()
        # Get all IP addresses associated with hostname
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        # Filter out loopback addresses
        local_ips = [ip for ip in ip_addresses if not ip.startswith("127.")]
        return local_ips
    except Exception as e:
        return [f"Error: {e}"]

def get_public_ip():
    """Get public IP (what others see)"""
    try:
        response = requests.get('https://httpbin.org/ip', timeout=5)
        return response.json()['origin']
    except Exception as e:
        return f"Error: {e}"

def get_network_info():
    """Get comprehensive network information"""
    info = {
        'local_ip': get_local_ip(),
        'hostname_ip': get_local_ip_hostname(),
        'all_local_ips': get_all_local_ips(),
        'hostname': socket.gethostname(),
        'public_ip': get_public_ip()
    }
    return info

def get_server_url(port=5000):
    """Get the full server URL"""
    local_ip = get_local_ip()
    return f"http://{local_ip}:{port}"

def print_server_info(port=5000):
    """Print all server access information"""
    local_ip = get_local_ip()
    all_ips = get_all_local_ips()
    
    print("=== Server Access Information ===")
    print(f"Local access: http://localhost:{port}")
    print(f"Local access: http://127.0.0.1:{port}")
    print(f"Network access: http://{local_ip}:{port}")
    
    if len(all_ips) > 1:
        print("\nAll possible network addresses:")
        for ip in all_ips:
            if not ip.startswith("Error"):
                print(f"  http://{ip}:{port}")
    
    print(f"\nShare this URL with others on your network:")
    print(f"http://{local_ip}:{port}")

# Platform-specific methods (if the above don't work)
def get_ip_platform_specific():
    """Platform-specific IP detection"""
    system = platform.system().lower()
    
    if system == "windows":
        try:
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            # Parse ipconfig output for IPv4 addresses
            lines = result.stdout.split('\n')
            for line in lines:
                if 'IPv4 Address' in line and '192.168.' in line:
                    return line.split(':')[1].strip()
        except:
            pass
    
    elif system == "linux" or system == "darwin":  # Darwin is macOS
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            ips = result.stdout.strip().split()
            return ips[0] if ips else None
        except:
            pass
    
    return "Unable to detect"

# Usage examples
if __name__ == "__main__":
    print("=== IP Address Detection ===")
    print(f"Primary local IP: {get_local_ip()}")
    print(f"Hostname IP: {get_local_ip_hostname()}")
    print(f"All local IPs: {get_all_local_ips()}")
    print(f"Server URL: {get_server_url()}")
    print()
    print_server_info()
    
    # Full network info
    print("\n=== Complete Network Info ===")
    info = get_network_info()
    for key, value in info.items():
        print(f"{key}: {value}")