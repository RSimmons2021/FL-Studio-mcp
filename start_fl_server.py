import os
import sys
import subprocess
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="Start the FL Studio MCP Server")
    parser.add_argument("--port", type=int, default=9877, help="Port to run the server on (default: 9877)")
    parser.add_argument("--host", default="localhost", help="Host to bind the server to (default: localhost)")
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the server script
    server_script = os.path.join(script_dir, "MCP_Server", "fl_server.py")
    
    # Make sure the server script exists
    if not os.path.exists(server_script):
        print(f"Error: Server script not found at {server_script}")
        return 1
    
    # Start the server
    print(f"Starting FL Studio MCP Server on {args.host}:{args.port}...")
    try:
        # Run the server script with the specified host and port
        process = subprocess.Popen(
            [sys.executable, server_script, "--host", args.host, "--port", str(args.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Wait a moment for the server to start
        time.sleep(1)
        
        # Check if the process is still running
        if process.poll() is None:
            print("Server started successfully!")
            print("Press Ctrl+C to stop the server")
            
            # Print server output
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            
            # Wait for the process to finish
            return_code = process.wait()
            if return_code != 0:
                print(f"Server exited with code {return_code}")
                return return_code
        else:
            print("Server failed to start")
            return 1
    except KeyboardInterrupt:
        print("\nStopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("Server stopped")
    except Exception as e:
        print(f"Error starting server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
