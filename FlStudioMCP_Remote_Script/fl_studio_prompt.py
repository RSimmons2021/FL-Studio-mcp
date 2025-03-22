import socket
import json
import re
import random
import time
import argparse
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import os
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FLStudioPrompt")

# Constants
HOST = "localhost"
DEFAULT_PORT = 9877

# Add the parent directory to path to import client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all client functions directly to avoid name conflicts
from MCP_Server.fl_client import (
    get_fl_studio_client, create_midi_track as client_create_midi_track, 
    set_track_name as client_set_track_name, create_pattern as client_create_pattern, 
    add_notes_to_pattern as client_add_notes_to_pattern, set_tempo as client_set_tempo, 
    get_plugin_list as client_get_plugin_list, load_plugin as client_load_plugin, 
    set_simulation_mode, get_simulation_mode
)

# Helper class to redirect stdout to the GUI
class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        self.original_stdout = sys.stdout
        sys.stdout = self
    
    def write(self, text):
        self.buffer += text
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)
    
    def flush(self):
        self.buffer = ""
        
    def __del__(self):
        sys.stdout = self.original_stdout

# Client wrappers to avoid name conflicts
def create_midi_track():
    """Create a MIDI track in FL Studio"""
    try:
        result = client_create_midi_track()
        return result
    except Exception as e:
        logger.error(f"Error creating MIDI track: {str(e)}")
        return None


def set_track_name(track_index, name):
    """Set the name of a track in FL Studio"""
    try:
        result = client_set_track_name(track_index, name)
        return result
    except Exception as e:
        logger.error(f"Error setting track name: {str(e)}")
        return None

def get_plugin_list():
    """Get a list of available plugins in FL Studio"""
    try:
        result = client_get_plugin_list()
        return result
    except Exception as e:
        logger.error(f"Error getting plugin list: {str(e)}")
        return None


def load_plugin(track_index, plugin_name):
    """Load a plugin onto a track in FL Studio"""
    try:
        result = client_load_plugin(track_index, plugin_name)
        return result
    except Exception as e:
        logger.error(f"Error loading plugin: {str(e)}")
        return None


def create_pattern(name, length):
    """Create a new pattern in FL Studio"""
    try:
        result = client_create_pattern(name, length)
        return result
    except Exception as e:
        logger.error(f"Error creating pattern: {str(e)}")
        return None


def add_notes_to_pattern(pattern_index, track_index, notes):
    """Add notes to a pattern in FL Studio"""
    try:
        result = client_add_notes_to_pattern(pattern_index, track_index, notes)
        return result
    except Exception as e:
        logger.error(f"Error adding notes to pattern: {str(e)}")
        return None


def set_tempo(tempo):
    """Set the tempo of the session in FL Studio"""
    try:
        result = client_set_tempo(tempo)
        return result
    except Exception as e:
        logger.error(f"Error setting tempo: {str(e)}")
        return None

def create_track(name):
    """Create a track in FL Studio"""
    try:
        result = client_create_midi_track()
        if result and "index" in result:
            track_index = result["index"]
            name_result = client_set_track_name(track_index, name)
            if name_result:
                logger.info(f"Created track '{name}' at index {track_index}")
                return track_index
        return None
    except Exception as e:
        logger.error(f"Error creating track: {str(e)}")
        return None

def select_plugin_for_track(track_properties):
    """Select an appropriate plugin based on track properties"""
    instrument_type = track_properties.get("instrument_type")
    track_type = track_properties.get("track_type")
    genre = track_properties.get("genre")
    
    try:
        # Get available plugins - in simulation mode this will return a simulated list
        plugin_result = client_get_plugin_list()
        available_plugins = plugin_result.get("plugins", [])
    except Exception as e:
        logger.warning(f"Could not get plugin list: {str(e)}")
        available_plugins = ["FLEX", "Fruity DX10", "Sytrus", "GMS", "FPC", "DirectWave"]
    
    # Map instrument types to likely plugins
    plugin_mapping = {
        "piano": ["FLEX", "DirectWave"],
        "synth": ["FLEX", "Sytrus", "Harmor", "GMS"],
        "bass": ["FLEX", "Sytrus", "GMS", "Harmor"],
        "lead": ["FLEX", "Sytrus", "Harmor"],
        "pad": ["FLEX", "Harmor", "Sytrus"],
        "strings": ["FLEX", "DirectWave"],
        "brass": ["FLEX", "DirectWave"],
        "guitar": ["FLEX", "DirectWave"],
        "drums": ["FPC", "DrumSynth Live"],
        "percussion": ["FPC", "DrumSynth Live"]
    }
    
    # Get plugins that match the instrument type
    matching_plugins = plugin_mapping.get(instrument_type, ["FLEX"])
    
    # Find the first available plugin that matches
    for plugin in matching_plugins:
        if plugin in available_plugins:
            return plugin
    
    # Default to FLEX if no match found
    if "FLEX" in available_plugins:
        return "FLEX"
    
    # Return the first available plugin as a last resort
    return available_plugins[0] if available_plugins else "FLEX"

def generate_notes_for_track(track_properties):
    """Generate MIDI notes based on track properties"""
    print("DEBUG: Starting generate_notes_for_track")
    print(f"DEBUG: Track properties: {json.dumps(track_properties, indent=2)}")
    notes = []
    
    # Define the MIDI note numbers for each key
    key_base_notes = {
        "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, 
        "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11
    }
    
    # Define scale patterns (semitone intervals)
    scale_patterns = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10]
    }
    
    # Get the base note for the key - ensure key is uppercase and a string
    key = str(track_properties.get("key", "C")).upper()
    print(f"DEBUG: Key = {key}, type = {type(key)}")
    base_key = key_base_notes.get(key, 0)  # Default to C if key not found
    print(f"DEBUG: Base key = {base_key}, type = {type(base_key)}")
    
    # Get the scale pattern - ensure scale is lowercase and a string
    scale = str(track_properties.get("scale", "major")).lower()
    print(f"DEBUG: Scale = {scale}, type = {type(scale)}")
    scale_pattern = scale_patterns.get(scale, scale_patterns["major"])  # Default to major if scale not found
    print(f"DEBUG: Scale pattern = {scale_pattern}")
    
    # Base octaves for different track types
    base_octaves = {
        "bass": 2,      # C2 = 36
        "lead": 4,      # C4 = 60
        "pad": 3,       # C3 = 48
        "chords": 3,    # C3 = 48
        "drums": 3,     # Not really used for drums
        "fx": 5         # C5 = 72
    }
    
    # Get the base octave for the track type
    track_type = str(track_properties.get("track_type", "unknown")).lower()
    print(f"DEBUG: Track type = {track_type}, type = {type(track_type)}")
    base_octave = base_octaves.get(track_type, 4)  # Default to octave 4 if track type not found
    print(f"DEBUG: Base octave = {base_octave}, type = {type(base_octave)}")
    
    # Generate available notes in the key and scale
    available_notes = []
    
    # Special case for drums - use standard drum mapping
    if track_type == "drums":
        available_notes = [36, 38, 42, 46]  # Kick, Snare, Closed HH, Open HH
    else:
        try:
            # Generate notes for 2 octaves in the selected key and scale
            for octave in range(base_octave, base_octave + 2):
                for interval in scale_pattern:
                    note = (octave * 12) + base_key + interval
                    available_notes.append(note)
        except Exception as e:
            print(f"DEBUG: Error generating notes: {str(e)}")
            # Fallback to C major scale in octave 4
            for octave in range(4, 6):
                for interval in scale_patterns["major"]:
                    note = (octave * 12) + interval
                    available_notes.append(note)
    
    print(f"DEBUG: Available notes = {available_notes}")
    
    # Ensure pattern_length is an integer
    try:
        pattern_length = int(track_properties.get("pattern_length", 16))
    except (ValueError, TypeError):
        pattern_length = 16  # Default to 16 steps if conversion fails
    
    print(f"DEBUG: Pattern length = {pattern_length}, type = {type(pattern_length)}")
    
    try:
        # Generate different patterns based on track type
        if track_type == "drums":
            # Simple drum pattern
            for i in range(pattern_length):
                # Kick on beats 1 and 9 (assuming 16 steps)
                if i % 4 == 0:
                    notes.append({"position": i, "note": 36, "length": 1, "velocity": 100})
                # Snare on beats 5 and 13
                if i % 8 == 4:
                    notes.append({"position": i, "note": 38, "length": 1, "velocity": 90})
                # Hi-hat on every other step
                if i % 2 == 0:
                    notes.append({"position": i, "note": 42, "length": 1, "velocity": 80})
        
        elif track_type == "bass":
            # Simple bass line
            for i in range(0, pattern_length, 4):
                note = random.choice(available_notes[:7])  # Use lower notes for bass
                notes.append({"position": i, "note": note, "length": 4, "velocity": 90})
        
        elif track_type == "chords":
            # Simple chord progression
            for i in range(0, pattern_length, 4):
                # Add a chord (multiple notes at once)
                root_idx = random.choice([0, 3, 4])  # I, IV, V chords
                if root_idx < len(available_notes):
                    root_note = available_notes[root_idx]
                    # Add triad (1-3-5)
                    notes.append({"position": i, "note": root_note, "length": 4, "velocity": 80})
                    if root_idx + 2 < len(available_notes):
                        notes.append({"position": i, "note": available_notes[root_idx + 2], "length": 4, "velocity": 80})
                    if root_idx + 4 < len(available_notes):
                        notes.append({"position": i, "note": available_notes[root_idx + 4], "length": 4, "velocity": 80})
        
        elif track_type == "pad":
            # Long sustained notes
            if available_notes:
                root_note = available_notes[0]  # Root note
                fifth_note = available_notes[4] if len(available_notes) > 4 else root_note + 7  # Fifth
                notes.append({"position": 0, "note": root_note, "length": pattern_length, "velocity": 70})
                notes.append({"position": 0, "note": fifth_note, "length": pattern_length, "velocity": 70})
            else:
                # Fallback if no available notes
                notes.append({"position": 0, "note": 60, "length": pattern_length, "velocity": 70})  # Middle C
                notes.append({"position": 0, "note": 67, "length": pattern_length, "velocity": 70})  # G above middle C
        
        else:  # lead or unknown
            # Simple melody
            for i in range(0, pattern_length, 2):
                if random.random() > 0.3 and available_notes:  # 70% chance of placing a note
                    note = random.choice(available_notes)
                    length = random.choice([1, 2, 4])
                    notes.append({"position": i, "note": note, "length": length, "velocity": 85})
    except Exception as e:
        print(f"DEBUG: Error generating pattern: {str(e)}")
        # Add a single note as fallback
        notes.append({"position": 0, "note": 60, "length": 4, "velocity": 100})  # Middle C
    
    print(f"DEBUG: Generated {len(notes)} notes")
    return notes

def analyze_prompt(prompt):
    """Analyze a text prompt to determine track properties"""
    prompt = prompt.lower()
    
    # Initialize default properties
    properties = {
        "track_type": "unknown",
        "instrument_type": "unknown",
        "genre": "unknown",
        "tempo": None,
        "pattern_length": 16,
        "name": "AI Generated Track",
        "effects": [],
        "chord_progression": None,
        "key": "C",
        "scale": "major"
    }
    
    # Detect track type
    if any(word in prompt for word in ["bass", "808", "sub"]):
        properties["track_type"] = "bass"
    elif any(word in prompt for word in ["drum", "beat", "percussion", "kick", "snare", "hat"]):
        properties["track_type"] = "drums"
    elif any(word in prompt for word in ["lead", "melody", "synth", "arp", "arpeggiat"]):
        properties["track_type"] = "lead"
    elif any(word in prompt for word in ["pad", "ambient", "atmosphere", "background"]):
        properties["track_type"] = "pad"
    elif any(word in prompt for word in ["chord", "harmony", "progression"]):
        properties["track_type"] = "chords"
    elif any(word in prompt for word in ["fx", "effect", "transition", "riser", "impact"]):
        properties["track_type"] = "fx"
    
    # Detect instrument type (expanded)
    if any(word in prompt for word in ["piano", "keys", "keyboard", "grand"]):
        properties["instrument_type"] = "piano"
    elif any(word in prompt for word in ["guitar", "acoustic", "electric guitar", "distorted"]):
        properties["instrument_type"] = "guitar"
    elif any(word in prompt for word in ["strings", "violin", "cello", "viola", "orchestral", "orchestra"]):
        properties["instrument_type"] = "strings"
    elif any(word in prompt for word in ["brass", "trumpet", "trombone", "horn", "saxophone", "sax"]):
        properties["instrument_type"] = "brass"
    elif any(word in prompt for word in ["synth", "synthesizer", "analog", "digital", "wavetable"]):
        properties["instrument_type"] = "synth"
    elif any(word in prompt for word in ["organ", "hammond", "church"]):
        properties["instrument_type"] = "organ"
    elif any(word in prompt for word in ["flute", "woodwind", "clarinet", "oboe"]):
        properties["instrument_type"] = "woodwind"
    elif any(word in prompt for word in ["vocal", "voice", "choir", "singing"]):
        properties["instrument_type"] = "vocal"
    
    # Detect genre (expanded)
    genres = {
        "edm": ["edm", "electronic", "dance", "house", "techno", "trance", "dubstep"],
        "hip hop": ["hip hop", "rap", "trap", "drill", "boom bap"],
        "rock": ["rock", "alternative", "indie", "metal", "punk"],
        "pop": ["pop", "mainstream", "chart"],
        "jazz": ["jazz", "blues", "swing", "bebop"],
        "classical": ["classical", "orchestral", "orchestra", "symphony"],
        "ambient": ["ambient", "chill", "relaxing", "atmospheric"],
        "r&b": ["r&b", "rnb", "soul", "funk"],
        "reggae": ["reggae", "dub", "dancehall"],
        "folk": ["folk", "acoustic", "country"]
    }
    
    for genre, keywords in genres.items():
        if any(keyword in prompt for keyword in keywords):
            properties["genre"] = genre
            break
    
    # Extract tempo if mentioned
    tempo_match = re.search(r'(\d+)\s*bpm', prompt)
    if tempo_match:
        properties["tempo"] = int(tempo_match.group(1))
    
    # Extract pattern length if mentioned
    length_match = re.search(r'(\d+)\s*bars?', prompt)
    if length_match:
        properties["pattern_length"] = int(length_match.group(1)) * 4  # Convert bars to beats (assuming 4/4)
    
    # Detect effects
    effects = {
        "reverb": ["reverb", "hall", "room", "space", "echo"],
        "delay": ["delay", "echo", "repeat"],
        "distortion": ["distortion", "distorted", "overdrive", "fuzz"],
        "chorus": ["chorus", "flanger", "phaser"],
        "compression": ["compression", "compressor", "squash"],
        "eq": ["eq", "equalizer", "equalization"],
        "filter": ["filter", "lowpass", "highpass", "bandpass"],
        "sidechain": ["sidechain", "pumping", "ducking"]
    }
    
    for effect, keywords in effects.items():
        if any(keyword in prompt for keyword in keywords):
            properties["effects"].append(effect)
    
    # Detect chord progression
    chord_progressions = {
        "I-IV-V": ["i-iv-v", "1-4-5"],
        "I-V-vi-IV": ["i-v-vi-iv", "1-5-6-4", "pop progression"],
        "ii-V-I": ["ii-v-i", "2-5-1", "jazz progression"],
        "I-vi-IV-V": ["i-vi-iv-v", "1-6-4-5", "50s progression"],
        "vi-IV-I-V": ["vi-iv-i-v", "6-4-1-5", "sad progression"]
    }
    
    for progression, keywords in chord_progressions.items():
        if any(keyword in prompt for keyword in keywords):
            properties["chord_progression"] = progression
            break
    
    # Detect key
    keys = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]
    for key in keys:
        key_pattern = re.compile(rf'\b{re.escape(key)}\b|\b{re.escape(key)}\s+minor\b|\b{re.escape(key)}m\b', re.IGNORECASE)
        if key_pattern.search(prompt):
            properties["key"] = key.upper()
            # Check for minor scale
            minor_pattern = re.compile(rf'\b{re.escape(key)}\s+minor\b|\b{re.escape(key)}m\b', re.IGNORECASE)
            if minor_pattern.search(prompt):
                properties["scale"] = "minor"
            break
    
    # Generate a name based on the properties
    if properties["track_type"] != "unknown":
        name_parts = []
        if properties["genre"] != "unknown":
            name_parts.append(properties["genre"].title())
        if properties["instrument_type"] != "unknown":
            name_parts.append(properties["instrument_type"].title())
        name_parts.append(properties["track_type"].title())
        properties["name"] = " ".join(name_parts)
    
    return properties

def create_track_from_prompt(prompt, log_callback=print):
    """Create a track based on a natural language prompt"""
    log_callback(f"Analyzing prompt: '{prompt}'")
    
    track_properties = analyze_prompt(prompt)
    log_callback(f"Detected properties: {json.dumps(track_properties, indent=2)}")
    
    try:
        # Create a track
        track_index = create_track(track_properties["name"])
        if track_index is None:
            log_callback("Failed to create track. Check FL Studio connection or try simulation mode.")
            return None
        
        log_callback(f"Created track '{track_properties['name']}' at index {track_index}")
        
        # Set tempo if specified
        if track_properties.get("tempo"):
            try:
                tempo_result = set_tempo(track_properties["tempo"])
                if tempo_result:
                    log_callback(f"Set tempo to {track_properties['tempo']} BPM")
            except Exception as e:
                log_callback(f"Error setting tempo: {str(e)}")
        
        # Select and load a plugin
        try:
            plugin_name = select_plugin_for_track(track_properties)
            log_callback(f"Selected plugin: {plugin_name}")
            
            plugin_result = load_plugin(track_index, plugin_name)
            if plugin_result:
                log_callback(f"Loaded plugin '{plugin_name}' on track {track_index}")
            else:
                log_callback(f"Failed to load plugin '{plugin_name}'")
        except Exception as e:
            log_callback(f"Error loading plugin: {str(e)}")
        
        # Create a pattern
        try:
            pattern_name = f"{track_properties['name']} Pattern"
            pattern_length = track_properties.get("pattern_length", 16)
            
            pattern_result = create_pattern(pattern_name, pattern_length)
            if pattern_result and "index" in pattern_result:
                pattern_index = pattern_result["index"]
                log_callback(f"Created pattern '{pattern_name}' with length {pattern_length} at index {pattern_index}")
                
                # Generate and add notes to the pattern
                try:
                    notes = generate_notes_for_track(track_properties)
                    log_callback(f"Generated {len(notes)} notes")
                    
                    notes_result = add_notes_to_pattern(pattern_index, track_index, notes)
                    if notes_result:
                        log_callback(f"Added notes to pattern {pattern_index}")
                    else:
                        log_callback("Failed to add notes to pattern")
                except Exception as e:
                    log_callback(f"Error adding notes: {str(e)}")
            else:
                log_callback("Failed to create pattern")
        except Exception as e:
            log_callback(f"Error creating pattern: {str(e)}")
        
        # Add effects if specified
        if track_properties.get("effects"):
            try:
                effects_added = load_plugin(track_index, track_properties["effects"][0])
                if effects_added:
                    log_callback(f"Added effects: {', '.join(track_properties['effects'])}")
            except Exception as e:
                log_callback(f"Error adding effects: {str(e)}")
        
        log_callback(f"\nTrack creation complete for '{track_properties['name']}'")
        log_callback(f"Plugin: {plugin_name}")
        log_callback(f"Pattern: {pattern_name} ({pattern_length} steps)")
        if track_properties.get("tempo"):
            log_callback(f"Tempo: {track_properties['tempo']} BPM")
        
        return track_index
    
    except Exception as e:
        log_callback(f"Error creating track: {str(e)}")
        import traceback
        log_callback(traceback.format_exc())
        return None


class TrackCreatorApp:
    """GUI Application for creating tracks based on natural language prompts"""
    def __init__(self, master):
        self.master = master
        master.title("FL Studio Track Creator")
        master.geometry("800x600")
        master.minsize(600, 400)
        
        # Set up dark mode colors
        self.bg_color = "#2D2D2D"  # Dark background
        self.fg_color = "#E0E0E0"  # Light text
        self.accent_color = "#FF8C00"  # FL Studio orange accent
        self.input_bg = "#3D3D3D"  # Slightly lighter background for inputs
        self.button_bg = "#FF8C00"  # FL Studio orange for buttons
        self.button_fg = "#1A1A1A"  # Dark text for buttons
        
        # Apply dark theme to the root window
        master.configure(bg=self.bg_color)
        
        # Define preset prompts
        self.preset_prompts = [
            "Create a synth lead with reverb",
            "Make a hip hop drum beat at 90 BPM",
            "Create a techno bass track in F minor",
            "Add a pad with delay effect",
            "Create an orchestral strings track with vibrato",
            "Make a trap beat with 808 bass",
            "Create a jazz piano with chords",
            "Add a EDM pluck synth with filter"
        ]
        
        # Main frame
        main_frame = tk.Frame(master, padx=20, pady=20, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = tk.Label(main_frame, text="FL Studio Track Creator", font=("Arial", 16, "bold"),
                             bg=self.bg_color, fg=self.accent_color)
        title_label.pack(pady=(0, 20))
        
        # Prompt frame
        prompt_frame = tk.Frame(main_frame, bg=self.bg_color)
        prompt_frame.pack(fill=tk.X, pady=10)
        
        prompt_label = tk.Label(prompt_frame, text="Describe your track:", font=("Arial", 12),
                              bg=self.bg_color, fg=self.fg_color)
        prompt_label.pack(side=tk.LEFT, padx=5)
        
        self.prompt_entry = tk.Entry(prompt_frame, font=("Arial", 12), width=40,
                                  bg=self.input_bg, fg=self.fg_color, insertbackground=self.fg_color)
        self.prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.prompt_entry.bind("<Return>", self.create_track)
        
        create_button = tk.Button(prompt_frame, text="Create Track", command=self.create_track,
                                font=("Arial", 12, "bold"), bg=self.button_bg, fg=self.button_fg,
                                activebackground=self.accent_color, activeforeground=self.button_fg)
        create_button.pack(side=tk.LEFT, padx=5)
        
        # Simulation mode checkbox
        self.simulation_var = tk.BooleanVar(value=get_simulation_mode())
        simulation_check = tk.Checkbutton(prompt_frame, text="Simulation Mode", variable=self.simulation_var,
                                        command=self.toggle_simulation_mode, font=("Arial", 10),
                                        bg=self.bg_color, fg=self.fg_color, selectcolor=self.input_bg,
                                        activebackground=self.bg_color, activeforeground=self.accent_color)
        simulation_check.pack(side=tk.LEFT, padx=5)
        
        # Preset prompts frame
        presets_frame = tk.Frame(main_frame, bg=self.bg_color)
        presets_frame.pack(fill=tk.X, pady=10)
        
        presets_label = tk.Label(presets_frame, text="Preset Prompts:", font=("Arial", 12),
                              bg=self.bg_color, fg=self.fg_color)
        presets_label.pack(anchor=tk.W, padx=5)
        
        # Create buttons for preset prompts in a grid
        preset_buttons_frame = tk.Frame(presets_frame, bg=self.bg_color)
        preset_buttons_frame.pack(fill=tk.X, padx=5)
        
        for i, prompt in enumerate(self.preset_prompts):
            row = i // 2
            col = i % 2
            
            button = tk.Button(preset_buttons_frame, text=prompt, 
                             command=lambda p=prompt: self.use_preset_prompt(p),
                             bg=self.input_bg, fg=self.fg_color,
                             activebackground=self.accent_color, activeforeground=self.button_fg)
            button.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        # Configure grid columns to expand equally
        preset_buttons_frame.columnconfigure(0, weight=1)
        preset_buttons_frame.columnconfigure(1, weight=1)
        
        # Log display
        log_frame = tk.Frame(main_frame, bg=self.bg_color)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        log_label = tk.Label(log_frame, text="Log:", font=("Arial", 12), anchor="w",
                            bg=self.bg_color, fg=self.fg_color)
        log_label.pack(fill=tk.X)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, font=("Courier", 10),
                                           bg=self.input_bg, fg=self.fg_color, insertbackground=self.fg_color)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W,
                            bg=self.input_bg, fg=self.fg_color)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Set up redirect for stdout
        self.stdout_redirect = StdoutRedirector(self.log_text)
        
    def toggle_simulation_mode(self):
        """Toggle simulation mode on/off"""
        new_state = self.simulation_var.get()
        set_simulation_mode(new_state)
        self.log(f"Simulation mode {'enabled' if new_state else 'disabled'}")
        
    def use_preset_prompt(self, prompt):
        """Fill the prompt entry with a preset prompt"""
        self.prompt_entry.delete(0, tk.END)
        self.prompt_entry.insert(0, prompt)
        
    def create_track(self, event=None):
        """Handle track creation button click"""
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("Empty Prompt", "Please enter a description for your track.")
            return
        
        # Clear log and update status
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("Creating track...")
        self.master.update()  # Update the UI
        
        # Create track in a separate thread to avoid freezing the UI
        threading.Thread(target=self._create_track_thread, args=(prompt,), daemon=True).start()
        
    def _create_track_thread(self, prompt):
        """Background thread for track creation"""
        try:
            self.log(f"Creating track from prompt: '{prompt}'")
            result = create_track_from_prompt(prompt, self.log)
            
            if result is not None:
                self.status_var.set("Track created successfully!")
            else:
                self.status_var.set("Track creation failed. See log for details.")
        except Exception:
            self.status_var.set("Error creating track")
            self.log(traceback.format_exc())
        
        # Ensure UI updates happen on the main thread
        self.master.after(0, self.scroll_to_end)
    
    def log(self, message):
        """Add a message to the log"""
        if isinstance(message, str):
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
    
    def scroll_to_end(self):
        """Scroll the log to the end"""
        self.log_text.see(tk.END)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FL Studio Track Creator")
    parser.add_argument("prompt", nargs="?", help="Natural language prompt describing the track to create")
    parser.add_argument("--sim", action="store_true", help="Run in simulation mode (when FL Studio is not running)")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical user interface")
    
    args = parser.parse_args()
    
    # Set simulation mode if requested
    if args.sim:
        set_simulation_mode(True)
    
    if args.gui or not args.prompt:
        # Launch GUI
        root = tk.Tk()
        app = TrackCreatorApp(root)
        root.mainloop()
    else:
        # Process command line prompt
        create_track_from_prompt(args.prompt)