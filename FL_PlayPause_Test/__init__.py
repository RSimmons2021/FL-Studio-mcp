# name=FL PlayPause Test
# url=https://github.com/RSimmons2021/FL-Studio-mcp
from __future__ import absolute_import, print_function, unicode_literals

import time
import os
import sys
import threading

# Get the script directory
script_dir = os.path.dirname(os.path.realpath(__file__))

# Create a log file in the script directory
log_path = os.path.join(script_dir, 'fl_playpause_test.log')

# GUI imports
try:
    import tkinter as tk
    from tkinter import scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Global variables
gui_window = None
log_text = None
log_queue = []
log_lock = threading.Lock()

def log_message(message):
    """Write a message to the log file and queue it for the GUI"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} - {message}"
    
    # Write to file
    try:
        with open(log_path, 'a') as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")
    
    # Add to queue for GUI
    with log_lock:
        log_queue.append(log_entry)
        
    # Print to console as well
    print(log_entry)

# Log script initialization
log_message("FL PlayPause Test script initializing...")
log_message(f"Script directory: {script_dir}")
log_message(f"Log file: {log_path}")

# Import FL Studio API modules
try:
    import transport
    import ui
    FL_STUDIO_API_AVAILABLE = True
    log_message("FL Studio API modules loaded successfully")
except ImportError:
    FL_STUDIO_API_AVAILABLE = False
    log_message("FL Studio API modules not available")

def create_gui():
    """Create a simple GUI to display logs"""
    global gui_window, log_text
    
    if not TKINTER_AVAILABLE:
        log_message("Tkinter not available, cannot create GUI")
        return
    
    # Create the main window
    gui_window = tk.Tk()
    gui_window.title("FL PlayPause Test")
    gui_window.geometry("600x400")
    
    # Create a frame for the log display
    frame = tk.Frame(gui_window)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Add a label
    label = tk.Label(frame, text="FL Studio PlayPause Test Log")
    label.pack(pady=(0, 5))
    
    # Create a scrolled text widget for logs
    log_text = scrolledtext.ScrolledText(frame, width=70, height=20)
    log_text.pack(fill=tk.BOTH, expand=True)
    log_text.config(state=tk.DISABLED)  # Make it read-only
    
    # Add buttons
    button_frame = tk.Frame(gui_window)
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    # Play/Pause button
    play_button = tk.Button(button_frame, text="Toggle Play/Pause", command=toggle_play_pause)
    play_button.pack(side=tk.LEFT, padx=5)
    
    # Clear log button
    clear_button = tk.Button(button_frame, text="Clear Log", command=clear_log)
    clear_button.pack(side=tk.LEFT, padx=5)
    
    # Status indicator
    status_frame = tk.Frame(gui_window)
    status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    status_label = tk.Label(status_frame, text="FL Studio API:")
    status_label.pack(side=tk.LEFT)
    
    status_indicator = tk.Label(
        status_frame, 
        text="Connected" if FL_STUDIO_API_AVAILABLE else "Not Connected",
        fg="green" if FL_STUDIO_API_AVAILABLE else "red"
    )
    status_indicator.pack(side=tk.LEFT, padx=5)
    
    # Set up periodic log update
    gui_window.after(100, update_log_display)
    
    return gui_window

def update_log_display():
    """Update the log display with queued messages"""
    global log_text, log_queue, gui_window
    
    if log_text and gui_window:
        # Get queued log entries
        entries = []
        with log_lock:
            if log_queue:
                entries = log_queue.copy()
                log_queue.clear()
        
        # Update the display
        if entries:
            log_text.config(state=tk.NORMAL)  # Make it writable
            for entry in entries:
                log_text.insert(tk.END, entry + "\n")
            log_text.see(tk.END)  # Scroll to the end
            log_text.config(state=tk.DISABLED)  # Make it read-only again
        
        # Schedule the next update
        gui_window.after(100, update_log_display)

def clear_log():
    """Clear the log display"""
    global log_text
    if log_text:
        log_text.config(state=tk.NORMAL)
        log_text.delete(1.0, tk.END)
        log_text.config(state=tk.DISABLED)
        log_message("Log cleared")

def toggle_play_pause():
    """Toggle play/pause in FL Studio"""
    if FL_STUDIO_API_AVAILABLE:
        try:
            # Toggle play/pause
            if transport.isPlaying():
                transport.stop()
                log_message("Playback stopped")
            else:
                transport.start()
                log_message("Playback started")
        except Exception as e:
            log_message(f"Error toggling play/pause: {e}")
    else:
        log_message("FL Studio API not available, cannot toggle play/pause")

def start_gui_thread():
    """Start the GUI in a separate thread"""
    if TKINTER_AVAILABLE:
        threading.Thread(target=run_gui, daemon=True).start()
        log_message("GUI thread started")
    else:
        log_message("Tkinter not available, cannot start GUI")

def run_gui():
    """Run the GUI main loop"""
    try:
        window = create_gui()
        if window:
            window.mainloop()
    except Exception as e:
        log_message(f"Error in GUI: {e}")

def create_instance(c_instance):
    """Create and return the script instance"""
    log_message("create_instance called")
    
    # Start the GUI in a separate thread
    start_gui_thread()
    
    return FLPlayPauseTest(c_instance)

class FLPlayPauseTest:
    """Simple FL Studio script to test play/pause functionality"""
    
    def __init__(self, c_instance):
        """Initialize the control surface"""
        self.c_instance = c_instance
        log_message("FLPlayPauseTest initialized")
        
        # Show a message in FL Studio
        if FL_STUDIO_API_AVAILABLE:
            try:
                ui.setHintMsg("FL PlayPause Test: Press F1 to toggle play/pause")
                log_message("Hint message set")
            except Exception as e:
                log_message(f"Error setting hint message: {e}")
    
    def disconnect(self):
        """Called when the script is disconnected"""
        log_message("FLPlayPauseTest disconnecting...")
        log_message("FLPlayPauseTest disconnected")
    
    def OnMidiMsg(self, event):
        """Handle MIDI messages"""
        pass  # Not used in this simple test
    
    def OnIdle(self):
        """Called during idle time"""
        pass  # Not used in this simple test
    
    def OnRefresh(self):
        """Called when the script should refresh its state"""
        pass  # Not used in this simple test
    
    def OnUpdateBeatIndicator(self, value):
        """Called when the beat indicator is updated"""
        pass  # Not used in this simple test
    
    def OnDisplayZone(self):
        """Called when the display zone changes"""
        pass  # Not used in this simple test
    
    def OnUpdateLiveMode(self, mode):
        """Called when live mode is updated"""
        pass  # Not used in this simple test
    
    def OnDirtyMixerTrack(self, index):
        """Called when a mixer track becomes dirty"""
        pass  # Not used in this simple test
    
    def OnNoteOn(self, event):
        """Called when a note on event is received"""
        pass  # Not used in this simple test
    
    def OnNoteOff(self, event):
        """Called when a note off event is received"""
        pass  # Not used in this simple test
    
    def OnControlChange(self, event):
        """Called when a control change event is received"""
        pass  # Not used in this simple test
    
    def OnProgramChange(self, event):
        """Called when a program change event is received"""
        pass  # Not used in this simple test
    
    def OnPitchBend(self, event):
        """Called when a pitch bend event is received"""
        pass  # Not used in this simple test
    
    def OnKeyPressEvent(self, event):
        """Called when a key is pressed"""
        log_message(f"Key press event: {event}")
        
        # Check if F1 key was pressed (key code 112)
        if event == 112 and FL_STUDIO_API_AVAILABLE:
            try:
                # Toggle play/pause
                if transport.isPlaying():
                    transport.stop()
                    ui.setHintMsg("Playback stopped")
                    log_message("Playback stopped")
                else:
                    transport.start()
                    ui.setHintMsg("Playback started")
                    log_message("Playback started")
                return True  # Event handled
            except Exception as e:
                log_message(f"Error toggling play/pause: {e}")
        
        return False  # Event not handled
