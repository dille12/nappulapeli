import string

alphabet = string.ascii_uppercase

def ip_to_code(ip):
    parts = ip.split(".")
    x, y = int(parts[2]), int(parts[3])
    n = (x << 8) | y  # combine into 16-bit
    code = ""
    for _ in range(4):
        n, r = divmod(n, 26)
        code = alphabet[r] + code
    return code

def code_to_ip(code):
    n = 0
    for c in code:
        n = n * 26 + alphabet.index(c)
    x, y = divmod(n, 256)
    return f"192.168.{x}.{y}"

# Example
ip = "192.168.42.123"
code = ip_to_code(ip)   # e.g. "BDZS"
print(code, code_to_ip(code))  # "BDZS 192.168.42.123"
