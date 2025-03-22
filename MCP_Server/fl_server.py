import socket
import json
import threading
import time
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FLStudioMCPServer")

class FLStudioServer:
    def __init__(self, host="localhost", port=9877):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self.client_threads = []
    
    def start(self):
        """Start the socket server"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host, self.port))
            self.server.listen(5)  # Allow up to 5 pending connections
            
            self.running = True
            logger.info(f"Server started on {self.host}:{self.port}")
            print(f"Server started on {self.host}:{self.port}")
            
            # Set a timeout to allow regular checking of running flag
            self.server.settimeout(1.0)
            
            # Main server loop
            while self.running:
                try:
                    client, address = self.server.accept()
                    logger.info(f"Client connected from {address}")
                    
                    # Start a new thread to handle this client
                    client_thread = threading.Thread(target=self._handle_client, args=(client, address))
                    client_thread.daemon = True
                    client_thread.start()
                    self.client_threads.append(client_thread)
                except socket.timeout:
                    # This is expected due to the timeout we set
                    pass
                except Exception as e:
                    if self.running:  # Only log if we're still supposed to be running
                        logger.error(f"Error accepting connection: {e}")
            
            logger.info("Server stopped")
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            print(f"Error starting server: {e}")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        # Close the server socket
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        # Wait for client threads to finish
        for thread in self.client_threads:
            if thread.is_alive():
                thread.join(0.5)  # Wait up to 0.5 seconds for each thread
        
        logger.info("Server stopped")
    
    def _handle_client(self, client, address):
        """Handle communication with a connected client"""
        try:
            # Set a small timeout to allow client to exit gracefully
            client.settimeout(0.5)
            
            # Keep connection open to process multiple commands
            while self.running:
                try:
                    # Receive data from the client
                    data = client.recv(8192).decode('utf-8')
                    if not data:
                        logger.info(f"Client {address} disconnected")
                        break
                    
                    logger.info(f"Received from {address}: {data[:100]}..." if len(data) > 100 else f"Received from {address}: {data}")
                    
                    # Parse the command
                    try:
                        command = json.loads(data)
                        response = self._process_command(command)
                    except json.JSONDecodeError:
                        response = {"status": "error", "message": "Invalid JSON"}
                    except Exception as e:
                        logger.error(f"Error processing command: {e}")
                        response = {"status": "error", "message": str(e)}
                    
                    # Send the response back to the client
                    client.sendall(json.dumps(response).encode('utf-8'))
                    
                    logger.info(f"Sent response to {address}: {json.dumps(response)[:100]}..." if len(json.dumps(response)) > 100 else f"Sent response to {address}: {json.dumps(response)}")
                    
                except socket.timeout:
                    # This is expected due to the timeout we set, just continue the loop
                    continue
                except ConnectionResetError:
                    logger.info(f"Connection reset by {address}")
                    break
                except Exception as e:
                    logger.error(f"Error receiving from client {address}: {e}")
                    break
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            # Close the connection
            try:
                client.close()
            except:
                pass
            logger.info(f"Connection closed with {address}")
    
    def _process_command(self, command):
        """Process a command from the client and return a response"""
        command_type = command.get("type")
        params = command.get("params", {})
        
        # Dispatch to the appropriate handler based on command type
        if command_type == "get_session_info":
            return self._get_session_info()
        elif command_type == "get_track_info":
            return self._get_track_info(params.get("track_index", 0))
        elif command_type == "create_midi_track":
            return self._create_midi_track(params.get("index", -1))
        elif command_type == "set_track_name":
            return self._set_track_name(params.get("track_index"), params.get("name"))
        elif command_type == "create_pattern":
            return self._create_pattern(params.get("name"), params.get("length", 16))
        elif command_type == "add_notes_to_pattern":
            return self._add_notes_to_pattern(params.get("pattern_index"), params.get("track_index"), params.get("notes", []))
        elif command_type == "set_pattern_name":
            return self._set_pattern_name(params.get("pattern_index"), params.get("name"))
        elif command_type == "set_tempo":
            return self._set_tempo(params.get("tempo"))
        elif command_type == "play_pattern":
            return self._play_pattern(params.get("pattern_index"))
        elif command_type == "stop_pattern":
            return self._stop_pattern(params.get("pattern_index"))
        elif command_type == "start_playback":
            return self._start_playback()
        elif command_type == "stop_playback":
            return self._stop_playback()
        elif command_type == "get_plugin_list":
            return self._get_plugin_list()
        elif command_type == "load_plugin":
            return self._load_plugin(params.get("track_index"), params.get("plugin_name"))
        else:
            return {"status": "error", "message": f"Unknown command type: {command_type}"}
    
    # Command implementations - these are simulated since we're not in FL Studio
    def _get_session_info(self):
        """Get information about the current session"""
        return {
            "status": "success",
            "result": {
                "tempo": 120,
                "signature_numerator": 4,
                "signature_denominator": 4,
                "track_count": 8,
                "master_track": {
                    "name": "Master",
                    "volume": 0.8,
                    "panning": 0.5
                }
            }
        }
    
    def _get_track_info(self, track_index):
        """Get information about a track"""
        return {
            "status": "success",
            "result": {
                "index": track_index,
                "name": f"Track {track_index}",
                "volume": 0.8,
                "panning": 0.5,
                "mute": False,
                "solo": False,
                "arm": False,
                "color": [0, 0, 255]
            }
        }
    
    def _create_midi_track(self, index):
        """Create a new MIDI track"""
        # In a real implementation, this would create a track in FL Studio
        # Here we just simulate success and return a track index
        try:
            # Convert index to integer if it's a string
            if isinstance(index, str):
                index = int(index)
            track_index = index if index >= 0 else 8  # Simulate adding at the end
            return {
                "status": "success",
                "result": {
                    "index": track_index
                }
            }
        except (ValueError, TypeError) as e:
            # Handle the case where index can't be converted to int
            return {
                "status": "error",
                "message": f"Invalid track index: {str(e)}"
            }
    
    def _set_track_name(self, track_index, name):
        """Set the name of a track"""
        if track_index is None or name is None:
            return {"status": "error", "message": "Missing track_index or name parameter"}
        
        return {"status": "success"}
    
    def _create_pattern(self, name, length):
        """Create a new pattern"""
        if name is None:
            return {"status": "error", "message": "Missing name parameter"}
        
        # Simulate creating a pattern
        pattern_index = 0  # In a real implementation, this would be the actual index
        return {
            "status": "success",
            "result": {
                "index": pattern_index
            }
        }
    
    def _add_notes_to_pattern(self, pattern_index, track_index, notes):
        """Add notes to a pattern"""
        if pattern_index is None or track_index is None or not notes:
            return {"status": "error", "message": "Missing pattern_index, track_index, or notes parameter"}
        
        return {"status": "success"}
    
    def _set_pattern_name(self, pattern_index, name):
        """Set the name of a pattern"""
        if pattern_index is None or name is None:
            return {"status": "error", "message": "Missing pattern_index or name parameter"}
        
        return {"status": "success"}
    
    def _set_tempo(self, tempo):
        """Set the tempo of the session"""
        if tempo is None:
            return {"status": "error", "message": "Missing tempo parameter"}
        
        return {"status": "success"}
    
    def _play_pattern(self, pattern_index):
        """Play a pattern"""
        if pattern_index is None:
            return {"status": "error", "message": "Missing pattern_index parameter"}
        
        return {"status": "success"}
    
    def _stop_pattern(self, pattern_index):
        """Stop a pattern"""
        if pattern_index is None:
            return {"status": "error", "message": "Missing pattern_index parameter"}
        
        return {"status": "success"}
    
    def _start_playback(self):
        """Start playback"""
        return {"status": "success"}
    
    def _stop_playback(self):
        """Stop playback"""
        return {"status": "success"}
    
    def _get_plugin_list(self):
        """Get a list of available plugins"""
        # Simulate a list of plugins
        plugins = [
            "3x Osc",
            "FLEX",
            "Sytrus",
            "Harmless",
            "Harmor",
            "FPC",
            "Slicex",
            "DirectWave",
            "Fruity Reeverb 2",
            "Fruity Delay 3",
            "Fruity Parametric EQ 2",
            "Fruity Limiter",
            "Fruity Compressor"
        ]
        
        return {
            "status": "success",
            "result": {
                "plugins": plugins
            }
        }
    
    def _load_plugin(self, track_index, plugin_name):
        """Load a plugin onto a track"""
        if track_index is None or plugin_name is None:
            return {"status": "error", "message": "Missing track_index or plugin_name parameter"}
        
        return {"status": "success"}

def main():
    parser = argparse.ArgumentParser(description="FL Studio MCP Server")
    parser.add_argument("--host", default="localhost", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=9877, help="Port to bind the server to")
    
    args = parser.parse_args()
    
    server = FLStudioServer(args.host, args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()

if __name__ == "__main__":
    main()
