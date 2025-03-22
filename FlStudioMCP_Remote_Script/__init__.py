# name= Fl Studio MCP
# url=
from __future__ import absolute_import, print_function, unicode_literals

import socket
import json
import threading
import time
import traceback
import queue

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
    import arrangement
    import playlist
    FL_STUDIO_API_AVAILABLE = True
except ImportError:
    FL_STUDIO_API_AVAILABLE = False
    print("FL Studio API modules not available. Running in simulation mode.")

# Constants for socket communication
DEFAULT_PORT = 9877
HOST = "localhost"

def create_instance(c_instance):
    """Create and return the FLStudioMCP script instance"""
    return FLStudioMCP(c_instance)

class FLStudioMCP:
    """FLStudioMCP Remote Script for FL Studio using DirectScript API"""
    
    def __init__(self, c_instance):
        """Initialize the control surface"""
        self.c_instance = c_instance
        self.log_message("FLStudioMCP Remote Script initializing...")
        
        # Socket server for communication
        self.server = None
        self.client_threads = []
        self.server_thread = None
        self.running = False
        
        # Start the socket server
        self.start_server()
        
        self.log_message("FLStudioMCP initialized")
        
        # Show a message
        self.show_message("FLStudioMCP: Listening for commands on port " + str(DEFAULT_PORT))
    
    def log_message(self, message):
        """Log a message"""
        print("[FLStudioMCP] " + message)
    
    def show_message(self, message):
        """Show a message in FL Studio's interface"""
        print("[FLStudioMCP] " + message)
        if FL_STUDIO_API_AVAILABLE:
            try:
                ui.setHintMsg(message)
            except:
                pass
    
    def disconnect(self):
        """Called when the script is disconnected"""
        self.log_message("FLStudioMCP disconnecting...")
        self.running = False
        
        # Stop the server
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        # Wait for the server thread to exit
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)
            
        # Clean up any client threads
        for client_thread in self.client_threads[:]:
            if client_thread.is_alive():
                # We don't join them as they might be stuck
                self.log_message(f"Client thread still alive during disconnect")
        
        self.log_message("FLStudioMCP disconnected")
    
    def start_server(self):
        """Start the socket server in a separate thread"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)  # Allow up to 5 pending connections
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_thread)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.log_message("Server started on port " + str(DEFAULT_PORT))
        except Exception as e:
            self.log_message("Error starting server: " + str(e))
            self.show_message("FLStudioMCP: Error starting server - " + str(e))
    
    def _server_thread(self):
        """Server thread implementation - handles client connections"""
        try:
            self.log_message("Server thread started")
            # Set a timeout to allow regular checking of running flag
            self.server.settimeout(1.0)
            
            while self.running:
                try:
                    # Accept connections with timeout
                    client, address = self.server.accept()
                    self.log_message("Connection accepted from " + str(address))
                    self.show_message("FLStudioMCP: Client connected")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # Keep track of client threads
                    self.client_threads.append(client_thread)
                    
                    # Clean up finished client threads
                    self.client_threads = [t for t in self.client_threads if t.is_alive()]
                    
                except socket.timeout:
                    # No connection yet, just continue
                    continue
                except Exception as e:
                    if self.running:  # Only log if still running
                        self.log_message("Server accept error: " + str(e))
                    time.sleep(0.5)
            
            self.log_message("Server thread stopped")
        except Exception as e:
            self.log_message("Server thread error: " + str(e))
    
    def _handle_client(self, client):
        """Handle communication with a connected client"""
        self.log_message("Client handler started")
        client.settimeout(None)  # No timeout for client socket
        buffer = b''
        
        try:
            while self.running:
                try:
                    # Receive data
                    data = client.recv(8192)
                    
                    if not data:
                        # Client disconnected
                        self.log_message("Client disconnected")
                        break
                    
                    # Accumulate data in buffer
                    buffer += data
                    
                    try:
                        # Try to parse command from buffer
                        command = json.loads(buffer.decode('utf-8'))
                        buffer = b''  # Clear buffer after successful parse
                        
                        self.log_message("Received command: " + str(command.get("type", "unknown")))
                        
                        # Process the command and get response
                        response = self._process_command(command)
                        
                        # Send the response
                        client.sendall(json.dumps(response).encode('utf-8'))
                    except json.JSONDecodeError:
                        # Incomplete data, wait for more
                        continue
                        
                except Exception as e:
                    self.log_message("Error handling client data: " + str(e))
                    self.log_message(traceback.format_exc())
                    
                    # Send error response if possible
                    error_response = {
                        "status": "error",
                        "message": str(e)
                    }
                    try:
                        client.sendall(json.dumps(error_response).encode('utf-8'))
                    except:
                        # If we can't send the error, the connection is probably dead
                        break
                    
                    # For serious errors, break the loop
                    if not isinstance(e, json.JSONDecodeError):
                        break
        except Exception as e:
            self.log_message("Error in client handler: " + str(e))
        finally:
            try:
                client.close()
            except:
                pass
            self.log_message("Client handler stopped")
    
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
            elif command_type == "get_track_info":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_info(track_index)
            # Commands that modify FL Studio's state
            elif command_type in ["create_midi_track", "set_track_name", 
                                 "create_pattern", "add_notes_to_pattern", "set_pattern_name", 
                                 "set_tempo", "play_pattern", "stop_pattern",
                                 "start_playback", "stop_playback", "load_plugin"]:
                # Use a thread-safe approach with a response queue
                response_queue = queue.Queue()
                
                # Define a function to execute
                def task():
                    try:
                        result = None
                        if command_type == "create_midi_track":
                            index = params.get("index", -1)
                            result = self._create_midi_track(index)
                        elif command_type == "set_track_name":
                            track_index = params.get("track_index", 0)
                            name = params.get("name", "")
                            result = self._set_track_name(track_index, name)
                        elif command_type == "create_pattern":
                            track_index = params.get("track_index", 0)
                            pattern_index = params.get("pattern_index", 0)
                            length = params.get("length", 4.0)
                            result = self._create_pattern(track_index, pattern_index, length)
                        elif command_type == "add_notes_to_pattern":
                            track_index = params.get("track_index", 0)
                            pattern_index = params.get("pattern_index", 0)
                            notes = params.get("notes", [])
                            result = self._add_notes_to_pattern(track_index, pattern_index, notes)
                        elif command_type == "set_pattern_name":
                            track_index = params.get("track_index", 0)
                            pattern_index = params.get("pattern_index", 0)
                            name = params.get("name", "")
                            result = self._set_pattern_name(track_index, pattern_index, name)
                        elif command_type == "set_tempo":
                            tempo = params.get("tempo", 120.0)
                            result = self._set_tempo(tempo)
                        elif command_type == "play_pattern":
                            pattern_index = params.get("pattern_index", 0)
                            result = self._play_pattern(pattern_index)
                        elif command_type == "stop_pattern":
                            pattern_index = params.get("pattern_index", 0)
                            result = self._stop_pattern(pattern_index)
                        elif command_type == "start_playback":
                            result = self._start_playback()
                        elif command_type == "stop_playback":
                            result = self._stop_playback()
                        elif command_type == "load_plugin":
                            track_index = params.get("track_index", 0)
                            plugin_name = params.get("plugin_name", "")
                            result = self._load_plugin(track_index, plugin_name)
                        
                        # Put the result in the queue
                        response_queue.put({"status": "success", "result": result})
                    except Exception as e:
                        self.log_message("Error in task: " + str(e))
                        self.log_message(traceback.format_exc())
                        response_queue.put({"status": "error", "message": str(e)})
                
                # Execute the task
                task_thread = threading.Thread(target=task)
                task_thread.daemon = True
                task_thread.start()
                
                # Wait for the response with a timeout
                try:
                    task_response = response_queue.get(timeout=10.0)
                    if task_response.get("status") == "error":
                        response["status"] = "error"
                        response["message"] = task_response.get("message", "Unknown error")
                    else:
                        response["result"] = task_response.get("result", {})
                except queue.Empty:
                    response["status"] = "error"
                    response["message"] = "Timeout waiting for operation to complete"
            elif command_type == "get_plugin_list":
                response["result"] = self._get_plugin_list()
            else:
                response["status"] = "error"
                response["message"] = "Unknown command: " + command_type
        except Exception as e:
            self.log_message("Error processing command: " + str(e))
            self.log_message(traceback.format_exc())
            response["status"] = "error"
            response["message"] = str(e)
        
        return response
    
    # Command implementations using FL Studio API
    
    def _get_session_info(self):
        """Get information about the current session"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "tempo": 140,
                    "signature_numerator": 4,
                    "signature_denominator": 4,
                    "track_count": 16,
                    "master_track": {
                        "name": "Master",
                        "volume": 0.8,
                        "panning": 0.5
                    }
                }
            
            # Get actual data from FL Studio API
            result = {
                "tempo": transport.getTempoInBPM(),
                "signature_numerator": transport.getTimeSignatureNumerator(),
                "signature_denominator": transport.getTimeSignatureDenominator(),
                "track_count": channels.channelCount(),
                "master_track": {
                    "name": "Master",
                    "volume": mixer.getTrackVolume(0),  # Master track is 0
                    "panning": mixer.getTrackPan(0)  # Master track is 0
                }
            }
            return result
        except Exception as e:
            self.log_message("Error getting session info: " + str(e))
            raise
    
    def _get_track_info(self, track_index):
        """Get information about a track (channel in FL Studio)"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "index": track_index,
                    "name": f"Channel {track_index + 1}",
                    "is_audio_track": False,
                    "is_midi_track": True,
                    "mute": False,
                    "solo": False,
                    "volume": 0.8,
                    "panning": 0.5,
                    "patterns": []
                }
            
            # Get actual data from FL Studio API
            channel_name = channels.getChannelName(track_index)
            channel_type = channels.getChannelType(track_index)
            
            # Get patterns that use this channel
            pattern_list = []
            pattern_count = patterns.patternCount()
            for i in range(pattern_count):
                # Check if this pattern uses this channel
                # This is a simplified approach - in reality, you'd need to check
                # if the pattern contains notes for this channel
                pattern_list.append({
                    "index": i,
                    "name": patterns.getPatternName(i)
                })
            
            result = {
                "index": track_index,
                "name": channel_name,
                "is_audio_track": channel_type == channels.CT_AUDIOTRACK,
                "is_midi_track": channel_type == channels.CT_MIDIINPUT,
                "mute": channels.isChannelMuted(track_index),
                "solo": channels.isChannelSolo(track_index),
                "volume": channels.getChannelVolume(track_index),
                "panning": channels.getChannelPan(track_index),
                "patterns": pattern_list
            }
            return result
        except Exception as e:
            self.log_message("Error getting track info: " + str(e))
            raise
    
    def _create_midi_track(self, index):
        """Create a new channel in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "index": index if index >= 0 else 0,
                    "name": f"Channel {index + 1 if index >= 0 else 1}"
                }
            
            # Create a new channel in FL Studio
            # Note: FL Studio doesn't have a direct API to create a channel at a specific index
            # So we create a new channel and then get its index
            channels.selectAll()
            channels.deselectAll()
            ui.showWindow(midi.widChannelRack)
            
            # Add a new channel
            new_channel_index = channels.channelCount()
            # This is a workaround - in real implementation you'd use the appropriate API call
            # For example, you might use a menu command to add a new channel
            general.processRECEvent(midi.REC_AddChannel, 0)
            
            # Wait a bit for the channel to be created
            time.sleep(0.1)
            
            # Get the name of the new channel
            channel_name = channels.getChannelName(new_channel_index)
            
            result = {
                "index": new_channel_index,
                "name": channel_name
            }
            return result
        except Exception as e:
            self.log_message("Error creating MIDI track: " + str(e))
            raise
    
    def _set_track_name(self, track_index, name):
        """Set the name of a channel in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "name": name
                }
            
            # Set the name of the channel
            channels.setChannelName(track_index, name)
            
            result = {
                "name": name
            }
            return result
        except Exception as e:
            self.log_message("Error setting track name: " + str(e))
            raise
    
    def _create_pattern(self, track_index, pattern_index, length):
        """Create a new pattern in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "name": f"Pattern {pattern_index + 1}",
                    "length": length
                }
            
            # Create a new pattern in FL Studio
            # If pattern_index is -1, create a new pattern
            if pattern_index == -1:
                pattern_index = patterns.patternCount()
                # Create a new pattern
                general.processRECEvent(midi.REC_NewPattern, 0)
            
            # Set the pattern length (in beats)
            # This is a simplified approach - in reality, you'd need to use the appropriate API call
            patterns.setPatternLength(pattern_index, length)
            
            # Get the pattern name
            pattern_name = patterns.getPatternName(pattern_index)
            
            result = {
                "name": pattern_name,
                "length": length
            }
            return result
        except Exception as e:
            self.log_message("Error creating pattern: " + str(e))
            raise
    
    def _add_notes_to_pattern(self, track_index, pattern_index, notes):
        """Add MIDI notes to a pattern in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "note_count": len(notes)
                }
            
            # Select the pattern
            patterns.jumpToPattern(pattern_index)
            
            # Select the channel
            channels.selectOneChannel(track_index)
            
            # Add notes to the pattern
            # This is a simplified approach - in reality, you'd need to use the appropriate API call
            for note in notes:
                # Extract note data
                pitch = note.get("pitch", 60)  # Default to middle C
                velocity = note.get("velocity", 100)
                position = note.get("position", 0)  # In ticks
                length = note.get("length", 240)  # In ticks (quarter note = 960 ticks)
                
                # Add the note
                # This is a placeholder - you'd need to use the appropriate API call
                # For example, you might use a piano roll API to add notes
                channels.addNote(track_index, pitch, velocity, position, length)
            
            result = {
                "note_count": len(notes)
            }
            return result
        except Exception as e:
            self.log_message("Error adding notes to pattern: " + str(e))
            raise
    
    def _set_pattern_name(self, track_index, pattern_index, name):
        """Set the name of a pattern in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "name": name
                }
            
            # Set the name of the pattern
            patterns.setPatternName(pattern_index, name)
            
            result = {
                "name": name
            }
            return result
        except Exception as e:
            self.log_message("Error setting pattern name: " + str(e))
            raise
    
    def _set_tempo(self, tempo):
        """Set the tempo of the session in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "tempo": tempo
                }
            
            # Set the tempo
            transport.setTempoInBPM(tempo)
            
            result = {
                "tempo": tempo
            }
            return result
        except Exception as e:
            self.log_message("Error setting tempo: " + str(e))
            raise
    
    def _play_pattern(self, pattern_index):
        """Play a pattern in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "playing": True,
                    "pattern_index": pattern_index
                }
            
            # Select the pattern
            patterns.jumpToPattern(pattern_index)
            
            # Start playback
            transport.start()
            
            result = {
                "playing": True,
                "pattern_index": pattern_index
            }
            return result
        except Exception as e:
            self.log_message("Error playing pattern: " + str(e))
            raise
    
    def _stop_pattern(self, pattern_index):
        """Stop a pattern in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "stopped": True,
                    "pattern_index": pattern_index
                }
            
            # Stop playback
            transport.stop()
            
            result = {
                "stopped": True,
                "pattern_index": pattern_index
            }
            return result
        except Exception as e:
            self.log_message("Error stopping pattern: " + str(e))
            raise
    
    def _start_playback(self):
        """Start playing the session in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "playing": True
                }
            
            # Start playback
            transport.start()
            
            result = {
                "playing": True
            }
            return result
        except Exception as e:
            self.log_message("Error starting playback: " + str(e))
            raise
    
    def _stop_playback(self):
        """Stop playing the session in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "playing": False
                }
            
            # Stop playback
            transport.stop()
            
            result = {
                "playing": False
            }
            return result
        except Exception as e:
            self.log_message("Error stopping playback: " + str(e))
            raise
    
    def _get_plugin_list(self):
        """Get a list of available plugins in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "plugins": [
                        {"name": "3x Osc", "type": "instrument"},
                        {"name": "FLEX", "type": "instrument"},
                        {"name": "Fruity Parametric EQ 2", "type": "effect"},
                        {"name": "Fruity Limiter", "type": "effect"},
                        {"name": "Fruity Reeverb 2", "type": "effect"},
                        {"name": "Fruity Delay 3", "type": "effect"},
                        {"name": "Fruity Compressor", "type": "effect"},
                        {"name": "Sytrus", "type": "instrument"},
                        {"name": "Harmor", "type": "instrument"},
                        {"name": "Fruity Chorus", "type": "effect"}
                    ]
                }
            
            # Get a list of plugins from FL Studio
            # This is a simplified approach - in reality, you'd need to use the appropriate API call
            plugin_list = []
            
            # Get generator plugins (instruments)
            generator_count = plugins.getPluginCount(plugins.GENERATOR)
            for i in range(generator_count):
                plugin_name = plugins.getPluginName(i, plugins.GENERATOR)
                plugin_list.append({
                    "name": plugin_name,
                    "type": "instrument"
                })
            
            # Get effect plugins
            effect_count = plugins.getPluginCount(plugins.EFFECT)
            for i in range(effect_count):
                plugin_name = plugins.getPluginName(i, plugins.EFFECT)
                plugin_list.append({
                    "name": plugin_name,
                    "type": "effect"
                })
            
            result = {
                "plugins": plugin_list
            }
            return result
        except Exception as e:
            self.log_message("Error getting plugin list: " + str(e))
            raise
    
    def _load_plugin(self, track_index, plugin_name):
        """Load a plugin onto a channel in FL Studio"""
        try:
            if not FL_STUDIO_API_AVAILABLE:
                # Simulated response when API is not available
                return {
                    "loaded": False,
                    "plugin_name": plugin_name,
                    "track_index": track_index,
                    "message": "FL Studio API not available. Please load the plugin manually."
                }
            
            # Select the channel
            channels.selectOneChannel(track_index)
            
            # Find the plugin
            plugin_found = False
            plugin_index = -1
            plugin_type = plugins.GENERATOR  # Default to generator (instrument)
            
            # Check if it's a generator plugin
            generator_count = plugins.getPluginCount(plugins.GENERATOR)
            for i in range(generator_count):
                if plugins.getPluginName(i, plugins.GENERATOR) == plugin_name:
                    plugin_found = True
                    plugin_index = i
                    plugin_type = plugins.GENERATOR
                    break
            
            # If not found, check if it's an effect plugin
            if not plugin_found:
                effect_count = plugins.getPluginCount(plugins.EFFECT)
                for i in range(effect_count):
                    if plugins.getPluginName(i, plugins.EFFECT) == plugin_name:
                        plugin_found = True
                        plugin_index = i
                        plugin_type = plugins.EFFECT
                        break
            
            if plugin_found:
                # Load the plugin onto the channel
                channels.addPlugin(track_index, plugin_index, plugin_type)
                
                result = {
                    "loaded": True,
                    "plugin_name": plugin_name,
                    "track_index": track_index
                }
            else:
                result = {
                    "loaded": False,
                    "plugin_name": plugin_name,
                    "track_index": track_index,
                    "message": f"Plugin '{plugin_name}' not found."
                }
            
            return result
        except Exception as e:
            self.log_message("Error loading plugin: " + str(e))
            raise