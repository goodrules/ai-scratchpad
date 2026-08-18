import socket
import sys

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

def main():
    db_host = "127.0.0.1"
    db_port = 5432
    toolbox_host = "127.0.0.1"
    toolbox_port = 5000

    print(f"Checking if PostgreSQL is running on {db_host}:{db_port}...")
    if check_port(db_host, db_port):
        print("✅ PostgreSQL port is open!")
    else:
        print("❌ PostgreSQL port is closed. Did you run 'docker-compose up -d'?")
        sys.exit(1)

    print(f"\nChecking if MCP Toolbox is running on {toolbox_host}:{toolbox_port}...")
    if check_port(toolbox_host, toolbox_port):
        print("✅ MCP Toolbox port is open!")
    else:
        print("ℹ️  MCP Toolbox port is closed. This is expected if you haven't started it yet.")
        print("To start it, run the binary as per README instructions (pointing to tools.yaml).")

if __name__ == "__main__":
    main()
