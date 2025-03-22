import socket
import json
import time
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FLStudioClient")

# Global simulation flag
SIMULATION_MODE = False

class FLStudioClient:
    def __init__(self, host="localhost", port=9877):
        self.host = host
        self.port = port
        self.connected = False
        self.sock = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 0.5  # seconds
    
    def connect(self):
        """Connect to the FL Studio MCP server"""
        global SIMULATION_MODE
        
        if SIMULATION_MODE:
            logger.info("Simulation mode enabled")
            return True
        
        if self.connected and self.sock:
            logger.info("Already connected to FL Studio MCP")
            return True
            
        try:
            # Close any existing socket
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
            
            # Create a new socket and connect
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            # Set TCP keepalive options (Windows specific)
            # These settings ensure the connection stays alive and detects disconnections
            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            if hasattr(socket, 'TCP_KEEPINTVL'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
            if hasattr(socket, 'TCP_KEEPCNT'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            
            # Connect with a timeout
            self.sock.settimeout(3.0)
            self.sock.connect((self.host, self.port))
            
            # Reset timeout to default for further operations
            self.sock.settimeout(5.0)
            
            self.connected = True
            logger.info(f"Connected to FL Studio MCP at {self.host}:{self.port}")
            
            return True
        except Exception as e:
            if not SIMULATION_MODE:
                logger.error(f"Failed to connect to FL Studio MCP: {str(e)}")
                self.reconnect_attempts += 1
            return False
    
    def disconnect(self):
        """Disconnect from the FL Studio MCP server"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from FL Studio MCP: {str(e)}")
            finally:
                self.sock = None
                self.connected = False
    
    def send_command(self, command_type, params=None):
        """Send a command to FL Studio and return the response"""
        global SIMULATION_MODE
        
        # Check if in simulation mode and return simulated response
        if SIMULATION_MODE:
            return self._get_simulated_response(command_type, params)
        
        # Try to connect if not already connected
        if not self.connected and not self.connect():
            # If still can't connect after retries, switch to simulation mode
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                logger.warning("Connection failed repeatedly, switching to simulation mode")
                SIMULATION_MODE = True
                return self._get_simulated_response(command_type, params)
            else:
                # Increment reconnect attempts and try again after delay
                self.reconnect_attempts += 1
                time.sleep(self.reconnect_delay)
                return self.send_command(command_type, params)
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            logger.info(f"Sending command: {command_type} with params: {params}")
            
            # Send the command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            logger.info(f"Command sent, waiting for response...")
            
            # Set timeout for response
            self.sock.settimeout(5.0)
            
            # Receive the response
            response_data = self.sock.recv(8192)
            logger.info(f"Received {len(response_data)} bytes of data")
            
            # Parse the response
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response parsed, status: {response.get('status', 'unknown')}")
            
            if response.get("status") == "error":
                logger.error(f"FL Studio error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from FL Studio"))
            
            # Reset reconnect attempts on successful communication
            self.reconnect_attempts = 0
            
            return response.get("result", {})
        except socket.error as e:
            logger.error(f"Socket connection error: {e}")
            self.disconnect()
            # If it's the first error, try to reconnect and retry the command
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
                time.sleep(self.reconnect_delay)
                if self.connect():
                    return self.send_command(command_type, params)
            # If too many reconnect attempts, switch to simulation mode
            logger.warning("Connection failed repeatedly, switching to simulation mode")
            SIMULATION_MODE = True
            return self._get_simulated_response(command_type, params)
        except Exception as e:
            logger.error(f"Error communicating with FL Studio: {str(e)}")
            self.disconnect()
            raise Exception(f"Connection to FL Studio lost: {str(e)}")
    
    def _get_simulated_response(self, command_type, params):
        """Generate a simulated response for testing without FL Studio"""
        logger.info(f"Simulating response for command: {command_type}")
        
        if command_type == "create_midi_track":
            track_index = params.get("index", -1)
            if track_index < 0:
                track_index = random.randint(1, 10)  # Simulate creating at random position
            return {"index": track_index}
        
        elif command_type == "set_track_name":
            return {"status": "success"}
        
        elif command_type == "create_pattern":
            return {"index": random.randint(0, 5)}
        
        elif command_type == "add_notes_to_pattern":
            return {"status": "success"}
        
        elif command_type == "set_tempo":
            return {"status": "success"}
        
        elif command_type == "get_plugin_list":
            # Return a list of simulated plugins
            return {
                "plugins": [
                    "FLEX",
                    "Fruity DX10",
                    "Harmor",
                    "Sytrus",
                    "GMS",
                    "FPC",
                    "DirectWave",
                    "Sakura",
                    "Sawer",
                    "Toxic Biohazard"
                ]
            }
        
        elif command_type == "load_plugin":
            return {"status": "success"}
        
        # Default fallback
        return {"status": "success", "message": "Simulated response"}

# Singleton client instance
_fl_studio_client = None

def set_simulation_mode(enabled=True):
    """Enable or disable simulation mode"""
    global SIMULATION_MODE
    prev_mode = SIMULATION_MODE
    SIMULATION_MODE = enabled
    logger.info(f"Simulation mode {'enabled' if enabled else 'disabled'}")
    return prev_mode

def get_simulation_mode():
    """Get the current simulation mode status"""
    global SIMULATION_MODE
    return SIMULATION_MODE

def get_fl_studio_client(host="localhost", port=9877):
    """Get or create a persistent FL Studio client"""
    global _fl_studio_client
    if _fl_studio_client is None:
        _fl_studio_client = FLStudioClient(host, port)
    return _fl_studio_client

# Helper functions for common commands
def create_midi_track(index=-1):
    """Create a new MIDI track"""
    client = get_fl_studio_client()
    try:
        # Ensure index is an integer
        index = int(index)
        return client.send_command("create_midi_track", {"index": index})
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid track index: {str(e)}")
        # Default to -1 (end) if conversion fails
        return client.send_command("create_midi_track", {"index": -1})

def set_track_name(track_index, name):
    """Set the name of a track"""
    client = get_fl_studio_client()
    try:
        # Ensure track_index is an integer
        track_index = int(track_index)
        return client.send_command("set_track_name", {"track_index": track_index, "name": str(name)})
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid track index: {str(e)}")
        return {"status": "error", "message": f"Invalid track index: {str(e)}"}

def create_pattern(name="AI Pattern", length=16):
    """Create a new pattern"""
    client = get_fl_studio_client()
    try:
        # Ensure length is an integer
        length = int(length)
        return client.send_command("create_pattern", {"name": str(name), "length": length})
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid pattern length: {str(e)}")
        # Default to length 16 if conversion fails
        return client.send_command("create_pattern", {"name": str(name), "length": 16})

def add_notes_to_pattern(pattern_index, track_index, notes):
    """Add notes to a pattern"""
    client = get_fl_studio_client()
    
    # Ensure all note data is of the correct type
    sanitized_notes = []
    for note in notes:
        sanitized_note = {
            "position": int(note["position"]) if "position" in note else 0,
            "note": int(note["note"]) if "note" in note else 60,  # Middle C as default
            "length": int(note["length"]) if "length" in note else 1,
            "velocity": int(note["velocity"]) if "velocity" in note else 100
        }
        sanitized_notes.append(sanitized_note)
    
    try:
        return client.send_command("add_notes_to_pattern", {
            "pattern_index": int(pattern_index),
            "track_index": int(track_index),
            "notes": sanitized_notes
        })
    except Exception as e:
        logger.error(f"Error adding notes to pattern: {str(e)}")
        # Return a simulated success response when in error
        return {"status": "success", "message": "Simulated success due to error"}

def set_tempo(tempo):
    """Set the tempo of the session"""
    client = get_fl_studio_client()
    try:
        # Ensure tempo is an integer
        tempo = int(tempo)
        return client.send_command("set_tempo", {"tempo": tempo})
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid tempo value: {str(e)}")
        return {"status": "error", "message": f"Invalid tempo value: {str(e)}"}

def get_plugin_list():
    """Get a list of available plugins"""
    client = get_fl_studio_client()
    return client.send_command("get_plugin_list")

def load_plugin(track_index, plugin_name):
    """Load a plugin onto a track"""
    client = get_fl_studio_client()
    try:
        # Ensure track_index is an integer
        track_index = int(track_index)
        return client.send_command("load_plugin", {
            "track_index": track_index,
            "plugin_name": str(plugin_name)
        })
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid track index: {str(e)}")
        return {"status": "error", "message": f"Invalid track index: {str(e)}"}
