import json
import re
import random
import time
import argparse
import sys
import os

# Add the parent directory to the path so we can import the MCP_Server module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from MCP_Server.fl_client import (
    get_fl_studio_client,
    client_create_midi_track as create_midi_track,
    client_set_track_name as set_track_name,
    client_create_pattern as client_create_pattern,
    client_add_notes_to_pattern as client_add_notes_to_pattern,
    client_set_tempo as set_tempo,
    client_load_plugin as client_load_plugin,
    client_get_plugin_list as client_get_plugin_list
)

def create_track(name="AI Generated Track"):
    """Create a new MIDI track"""
    try:
        # Create a new MIDI track
        result = create_midi_track(-1)
        if result is None:
            print("Error creating MIDI track")
            return None
            
        track_index = result.get("index", -1)
        
        # Set the track name
        name_result = set_track_name(track_index, name)
        if name_result is None:
            print(f"Error setting track name to {name}")
        
        return track_index
    except Exception as e:
        print(f"Error in create_track: {e}")
        return None

def get_available_plugins():
    """Get a list of available plugins"""
    try:
        return client_get_plugin_list()
    except Exception as e:
        print(f"Error getting plugin list: {e}")
        return []

def load_plugin(track_index, plugin_name):
    """Load a plugin onto a track"""
    try:
        result = client_load_plugin(track_index, plugin_name)
        return result is not None
    except Exception as e:
        print(f"Error loading plugin {plugin_name} onto track {track_index}: {e}")
        return False

def create_pattern(name="AI Pattern", length=16):
    """Create a new pattern"""
    try:
        result = client_create_pattern(name, length)
        if result is None:
            print("Error creating pattern")
            return None
            
        return result.get("index", -1)
    except Exception as e:
        print(f"Error creating pattern: {e}")
        return None

def add_notes_to_pattern(pattern_index, track_index, notes):
    """Add notes to a pattern"""
    try:
        result = client_add_notes_to_pattern(pattern_index, track_index, notes)
        return result is not None
    except Exception as e:
        print(f"Error adding notes to pattern {pattern_index}: {e}")
        return False

def add_effects_to_track(track_index, effects):
    """Add effects to a track (placeholder for now)"""
    print(f"Would add effects {effects} to track {track_index} - not implemented yet")
    return True

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
        "name": "AI Generated Track"
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
    
    # Detect instrument type
    if any(word in prompt for word in ["piano", "keys", "keyboard"]):
        properties["instrument_type"] = "piano"
    elif any(word in prompt for word in ["guitar", "acoustic", "electric guitar"]):
        properties["instrument_type"] = "guitar"
    elif any(word in prompt for word in ["strings", "violin", "cello", "viola", "orchestral"]):
        properties["instrument_type"] = "strings"
    elif any(word in prompt for word in ["brass", "trumpet", "trombone", "horn"]):
        properties["instrument_type"] = "brass"
    elif any(word in prompt for word in ["synth", "synthesizer", "analog", "digital"]):
        properties["instrument_type"] = "synth"
    
    # Detect genre
    genres = {
        "edm": ["edm", "electronic", "dance"],
        "hip hop": ["hip hop", "rap", "trap"],
        "rock": ["rock", "alternative", "indie"],
        "pop": ["pop", "mainstream"],
        "jazz": ["jazz", "blues"],
        "classical": ["classical", "orchestral", "orchestra"],
        "ambient": ["ambient", "chill", "relaxing"]
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

def select_plugin_for_track(track_properties):
    """Select an appropriate plugin based on track properties"""
    # These are common FL Studio plugins - adjust based on what's available
    plugin_mapping = {
        "bass": {
            "synth": ["3x Osc", "FLEX", "Sytrus"],
            "default": ["3x Osc"]
        },
        "drums": {
            "default": ["FPC", "Slicex"]
        },
        "lead": {
            "synth": ["FLEX", "Sytrus", "Harmless"],
            "piano": ["FLEX", "DirectWave"],
            "default": ["FLEX"]
        },
        "pad": {
            "synth": ["FLEX", "Harmless", "Sytrus"],
            "strings": ["FLEX", "DirectWave"],
            "default": ["FLEX"]
        },
        "chords": {
            "piano": ["FLEX", "DirectWave"],
            "synth": ["FLEX", "Sytrus"],
            "guitar": ["FLEX", "DirectWave"],
            "default": ["FLEX"]
        },
        "fx": {
            "default": ["FLEX", "Sytrus"]
        },
        "unknown": {
            "default": ["FLEX"]
        }
    }
    
    track_type = track_properties["track_type"]
    instrument_type = track_properties["instrument_type"]
    
    # Get the appropriate plugin list
    if track_type in plugin_mapping:
        if instrument_type in plugin_mapping[track_type]:
            plugin_list = plugin_mapping[track_type][instrument_type]
        else:
            plugin_list = plugin_mapping[track_type]["default"]
    else:
        plugin_list = plugin_mapping["unknown"]["default"]
    
    # Return the first plugin in the list
    return plugin_list[0]

def generate_notes_for_track(track_properties):
    """Generate MIDI notes based on track properties"""
    notes = []
    
    # Base note values for different track types
    base_notes = {
        "bass": [36, 38, 40, 41],  # C2, D2, E2, F2
        "lead": [60, 62, 64, 65, 67, 69, 71, 72],  # C4 to C5
        "pad": [48, 52, 55, 59],  # C3, E3, G3, B3 (Cmaj7)
        "chords": [48, 52, 55, 59],  # C3, E3, G3, B3 (Cmaj7)
        "drums": [36, 38, 42, 46],  # Kick, Snare, Closed HH, Open HH
        "fx": [72, 74, 76, 77, 79]  # C5 to G5
    }
    
    # Get the appropriate base notes
    if track_properties["track_type"] in base_notes:
        available_notes = base_notes[track_properties["track_type"]]
    else:
        available_notes = base_notes["lead"]  # Default to lead notes
    
    pattern_length = track_properties["pattern_length"]
    
    # Generate different patterns based on track type
    if track_properties["track_type"] == "drums":
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
    
    elif track_properties["track_type"] == "bass":
        # Simple bass line
        for i in range(0, pattern_length, 4):
            note = random.choice(available_notes)
            notes.append({"position": i, "note": note, "length": 4, "velocity": 90})
    
    elif track_properties["track_type"] == "chords":
        # Simple chord progression
        for i in range(0, pattern_length, 4):
            # Add a chord (multiple notes at once)
            chord_root = random.choice([48, 50, 52, 53, 55])  # C3, D3, E3, F3, G3
            notes.append({"position": i, "note": chord_root, "length": 4, "velocity": 80})
            notes.append({"position": i, "note": chord_root + 4, "length": 4, "velocity": 80})
            notes.append({"position": i, "note": chord_root + 7, "length": 4, "velocity": 80})
    
    elif track_properties["track_type"] == "pad":
        # Long sustained notes
        note = random.choice(available_notes)
        notes.append({"position": 0, "note": note, "length": pattern_length, "velocity": 70})
        notes.append({"position": 0, "note": note + 7, "length": pattern_length, "velocity": 70})  # Add a fifth
    
    else:  # lead or unknown
        # Simple melody
        for i in range(0, pattern_length, 2):
            if random.random() > 0.3:  # 70% chance of placing a note
                note = random.choice(available_notes)
                length = random.choice([1, 2, 4])
                notes.append({"position": i, "note": note, "length": length, "velocity": 85})
    
    return notes

def create_track_from_prompt(prompt, log_callback=print):
    """Create a track based on a natural language prompt"""
    log_callback(f"Analyzing prompt: '{prompt}'")
    
    # Analyze the prompt
    track_properties = analyze_prompt(prompt)
    log_callback(f"Detected properties: {json.dumps(track_properties, indent=2)}")
    
    # Create a track
    track_index = create_track(track_properties["name"])
    if track_index is None:
        return None
    
    # Select and load a plugin
    plugin_name = select_plugin_for_track(track_properties)
    log_callback(f"Selected plugin: {plugin_name}")
    
    plugin_loaded = load_plugin(track_index, plugin_name)
    if not plugin_loaded:
        log_callback("Could not load plugin, but continuing with track creation")
    
    # Set tempo if specified
    if track_properties["tempo"] is not None:
        tempo_set = set_tempo(track_properties["tempo"])
        if tempo_set:
            log_callback(f"Set tempo to {track_properties['tempo']} BPM")
    
    # Create a pattern
    pattern_name = f"{track_properties['name']} Pattern"
    pattern_index = create_pattern(pattern_name, track_properties["pattern_length"])
    if pattern_index is None:
        return track_index  # Return track index even if pattern creation failed
    
    # Generate and add notes
    notes = generate_notes_for_track(track_properties)
    notes_added = add_notes_to_pattern(pattern_index, track_index, notes)
    
    if notes_added:
        log_callback(f"Added {len(notes)} notes to pattern {pattern_index}")
    
    # Add effects if specified
    if track_properties.get("effects"):
        effects_added = add_effects_to_track(track_index, track_properties["effects"])
        if effects_added:
            log_callback(f"Added effects: {', '.join(track_properties['effects'])}")
    
    log_callback(f"\nTrack creation complete!")
    log_callback(f"Track: {track_properties['name']} (index {track_index})")
    log_callback(f"Plugin: {plugin_name}")
    log_callback(f"Pattern: {pattern_name} (index {pattern_index})")
    
    return track_index

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a track in FL Studio based on a prompt")
    parser.add_argument("prompt", nargs="?", default="Create a synth lead track", 
                        help="Natural language prompt describing the track to create")
    
    args = parser.parse_args()
    
    # Create a track based on the prompt
    create_track_from_prompt(args.prompt)
