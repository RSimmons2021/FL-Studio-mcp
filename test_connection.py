import socket
import json
import sys

def test_fl_studio_connection(host='localhost', port=9050):
    """Test if we can connect to the FL Studio MCP server"""
    print(f"Attempting to connect to FL Studio MCP at {host}:{port}...")
    
    try:
        # Create a socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)  # 5 second timeout
        
        # Connect to the server
        client.connect((host, port))
        print("Connected successfully!")
        
        # Try to get session info
        command = {
            "type": "get_session_info",
            "params": {}
        }
        
        # Send the command
        client.sendall(json.dumps(command).encode('utf-8'))
        print("Sent get_session_info command")
        
        # Receive the response
        response = client.recv(8192).decode('utf-8')
        print(f"Received response: {response}")
        
        # Parse the response
        response_data = json.loads(response)
        if response_data.get("status") == "success":
            print("\nConnection test successful! FL Studio MCP server is running.")
            print(f"Session info: {json.dumps(response_data.get('result', {}), indent=2)}")
        else:
            print(f"\nServer returned error: {response_data.get('message', 'Unknown error')}")
        
        # Close the connection
        client.close()
        
    except socket.timeout:
        print("\nConnection timed out. The server might be running but not responding.")
    except ConnectionRefusedError:
        print("\nConnection refused. The server is not running or not accepting connections.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_fl_studio_connection()
