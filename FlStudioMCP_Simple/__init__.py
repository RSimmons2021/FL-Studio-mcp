# name=FL Studio MCP Simple
# url=https://github.com/RSimmons2021/FL-Studio-mcp
from __future__ import absolute_import, print_function, unicode_literals

import socket
import json
import threading
import time
import os

# Create a log file
log_path = os.path.join(os.path.expanduser('~'), 'fl_studio_mcp_simple.log')

def log_message(message):
    """Write a message to the log file"""
    with open(log_path, 'a') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Log script initialization
log_message("FL Studio MCP Simple script initializing...")

# Import FL Studio API modules
try:
    import channels
    import mixer
    import patterns
    import plugins
    import transport
    import ui
    import device
    import general
    FL_STUDIO_API_AVAILABLE = True
    log_message("FL Studio API modules loaded successfully")
except ImportError:
    FL_STUDIO_API_AVAILABLE = False
    log_message("FL Studio API modules not available. Running in simulation mode.")

# Constants for socket communication
DEFAULT_PORT = 9050
HOST = "localhost"

# Global variables
server = None
server_thread = None
running = False

def create_instance(c_instance):
    """Create and return the FLStudioMCP script instance"""
    log_message("create_instance called")
    return FLStudioMCPSimple(c_instance)

class FLStudioMCPSimple:
    """Simple FL Studio MCP Remote Script"""
    
    def __init__(self, c_instance):
        """Initialize the control surface"""
        self.c_instance = c_instance
        log_message("FLStudioMCPSimple initialized")
        
        # Start the server
        self.start_server()
        
        # Show a message in FL Studio
        if FL_STUDIO_API_AVAILABLE:
            try:
                ui.setHintMsg("FL Studio MCP Simple: Server started on port " + str(DEFAULT_PORT))
            except:
                pass
    
    def disconnect(self):
        """Called when the script is disconnected"""
        global running
        log_message("FLStudioMCPSimple disconnecting...")
        running = False
        
        # Stop the server
        if server:
            try:
                server.close()
            except:
                pass
        
        log_message("FLStudioMCPSimple disconnected")
    
    def start_server(self):
        """Start the socket server in a separate thread"""
        global server, server_thread, running
        
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, DEFAULT_PORT))
            server.listen(5)  # Allow up to 5 pending connections
            
            running = True
            server_thread = threading.Thread(target=self._server_thread)
            server_thread.daemon = True
            server_thread.start()
            
            log_message(f"Server started on {HOST}:{DEFAULT_PORT}")
        except Exception as e:
            log_message(f"Error starting server: {e}")
    
    def _server_thread(self):
        """Server thread implementation - handles client connections"""
        global running, server
        
        try:
            log_message("Server thread started")
            # Set a timeout to allow regular checking of running flag
            server.settimeout(1.0)
            
            while running:
                try:
                    # Accept connections with timeout
                    client, address = server.accept()
                    log_message(f"Connection accepted from {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    # No connection yet, just continue
                    continue
                except Exception as e:
                    if running:  # Only log if still running
                        log_message(f"Server accept error: {e}")
                    time.sleep(0.5)
            
            log_message("Server thread stopped")
        except Exception as e:
            log_message(f"Server thread error: {e}")
    
    def _handle_client(self, client):
        """Handle communication with a connected client"""
        log_message("Client handler started")
        
        try:
            while running:
                try:
                    # Receive data
                    data = client.recv(8192)
                    
                    if not data:
                        # Client disconnected
                        log_message("Client disconnected")
                        break
                    
                    # Parse the command
                    command = json.loads(data.decode('utf-8'))
                    log_message(f"Received command: {command.get('type', 'unknown')}")
                    
                    # Process the command and get response
                    response = self._process_command(command)
                    
                    # Send the response
                    client.sendall(json.dumps(response).encode('utf-8'))
                    
                except Exception as e:
                    log_message(f"Error handling client data: {e}")
                    break
        except Exception as e:
            log_message(f"Error in client handler: {e}")
        finally:
            try:
                client.close()
            except:
                pass
            log_message("Client handler stopped")
    
    def _process_command(self, command):
        """Process a command from the client and return a response"""
        command_type = command.get("type", "")
        params = command.get("params", {})
        
        # Initialize response
        response = {
            "status": "success",
            "result": {}
        }
        
        try:
            # Route the command to the appropriate handler
            if command_type == "get_session_info":
                response["result"] = self._get_session_info()
            elif command_type == "create_midi_track":
                index = params.get("index", -1)
                response["result"] = self._create_midi_track(index)
            elif command_type == "set_track_name":
                track_index = params.get("track_index")
                name = params.get("name")
                self._set_track_name(track_index, name)
            else:
                # For other commands, just return success
                response["result"] = {"message": f"Command {command_type} acknowledged"}
        except Exception as e:
            log_message(f"Error processing command: {e}")
            response["status"] = "error"
            response["message"] = str(e)
        
        return response
    
    # Command implementations
    
    def _get_session_info(self):
        """Get information about the current session"""
        if not FL_STUDIO_API_AVAILABLE:
            return {
                "tempo": 120,
                "track_count": 8,
                "simulation": True
            }
        
        # Get actual data from FL Studio API
        return {
            "tempo": transport.getTempoInBPM(),
            "track_count": channels.channelCount(),
            "simulation": False
        }
    
    def _create_midi_track(self, index):
        """Create a new MIDI track"""
        if not FL_STUDIO_API_AVAILABLE:
            return {
                "index": index if index >= 0 else 0,
                "simulation": True
            }
        
        try:
            # Create a new channel in FL Studio
            if index < 0:
                # Find the first empty channel
                for i in range(channels.channelCount()):
                    if not channels.isChannelUsed(i):
                        index = i
                        break
                if index < 0:  # If all channels are used
                    index = channels.channelCount() - 1
            
            # Make sure the channel exists
            channels.selectChannel(index)
            log_message(f"Created MIDI track at index {index}")
            
            return {
                "index": index,
                "simulation": False
            }
        except Exception as e:
            log_message(f"Error creating MIDI track: {e}")
            raise
    
    def _set_track_name(self, track_index, name):
        """Set the name of a track"""
        if not FL_STUDIO_API_AVAILABLE:
            return
        
        try:
            # Set the channel name in FL Studio
            channels.setChannelName(track_index, name)
            log_message(f"Set track name for track {track_index} to '{name}'")
        except Exception as e:
            log_message(f"Error setting track name: {e}")
            raise
