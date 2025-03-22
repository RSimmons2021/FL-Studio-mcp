import socket
import json
import time
import tkinter as tk
from tkinter import scrolledtext
import threading

# GUI setup
root = tk.Tk()
root.title("FL Studio Connection Test")
root.geometry("600x500")

# Create log display
log_frame = tk.Frame(root)
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

log_label = tk.Label(log_frame, text="Connection Log")
log_label.pack(pady=(0, 5))

log_text = scrolledtext.ScrolledText(log_frame, width=70, height=20)
log_text.pack(fill=tk.BOTH, expand=True)
log_text.config(state=tk.DISABLED)

# Status display
status_frame = tk.Frame(root)
status_frame.pack(fill=tk.X, padx=10, pady=5)

status_label = tk.Label(status_frame, text="Status:")
status_label.pack(side=tk.LEFT)

connection_status = tk.Label(status_frame, text="Disconnected", fg="red")
connection_status.pack(side=tk.LEFT, padx=5)

# Control buttons
button_frame = tk.Frame(root)
button_frame.pack(fill=tk.X, padx=10, pady=10)

# Function to log messages
def log_message(message):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)
    print(message)

# Function to connect to FL Studio
def connect_to_fl_studio():
    global client
    host = 'localhost'
    port = 9050
    
    try:
        # Create a socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)  # 5 second timeout
        
        # Connect to the server
        log_message(f"Attempting to connect to FL Studio at {host}:{port}...")
        client.connect((host, port))
        log_message("Connected successfully!")
        
        # Update status
        connection_status.config(text="Connected", fg="green")
        connect_button.config(state=tk.DISABLED)
        disconnect_button.config(state=tk.NORMAL)
        play_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.NORMAL)
        create_track_button.config(state=tk.NORMAL)
        
        # Start listening for messages
        threading.Thread(target=listen_for_messages, daemon=True).start()
        
        return True
    except Exception as e:
        log_message(f"Connection failed: {e}")
        connection_status.config(text="Disconnected", fg="red")
        return False

# Function to disconnect
def disconnect_from_fl_studio():
    global client
    try:
        client.close()
        log_message("Disconnected from FL Studio")
    except Exception as e:
        log_message(f"Error disconnecting: {e}")
    
    # Update status
    connection_status.config(text="Disconnected", fg="red")
    connect_button.config(state=tk.NORMAL)
    disconnect_button.config(state=tk.DISABLED)
    play_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.DISABLED)
    create_track_button.config(state=tk.DISABLED)

# Function to listen for messages
def listen_for_messages():
    global client
    while True:
        try:
            data = client.recv(8192)
            if not data:
                log_message("Connection closed by server")
                break
            
            response = json.loads(data.decode('utf-8'))
            log_message(f"Received: {response}")
        except Exception as e:
            log_message(f"Error receiving data: {e}")
            break
    
    # Update UI when connection is lost
    root.after(0, lambda: connection_status.config(text="Disconnected", fg="red"))
    root.after(0, lambda: connect_button.config(state=tk.NORMAL))
    root.after(0, lambda: disconnect_button.config(state=tk.DISABLED))
    root.after(0, lambda: play_button.config(state=tk.DISABLED))
    root.after(0, lambda: stop_button.config(state=tk.DISABLED))
    root.after(0, lambda: create_track_button.config(state=tk.DISABLED))

# Function to send a command
def send_command(command_type, params=None):
    if params is None:
        params = {}
    
    command = {
        "type": command_type,
        "params": params
    }
    
    try:
        log_message(f"Sending command: {command_type}")
        client.sendall(json.dumps(command).encode('utf-8'))
    except Exception as e:
        log_message(f"Error sending command: {e}")

# Command functions
def start_playback():
    send_command("start_playback")

def stop_playback():
    send_command("stop_playback")

def create_track():
    send_command("create_midi_track", {"index": -1})
    # After creating track, set its name
    time.sleep(0.5)  # Small delay to ensure track is created
    send_command("set_track_name", {"track_index": 0, "name": "Test Track"})

# Create buttons
connect_button = tk.Button(button_frame, text="Connect", command=connect_to_fl_studio)
connect_button.pack(side=tk.LEFT, padx=5)

disconnect_button = tk.Button(button_frame, text="Disconnect", command=disconnect_from_fl_studio, state=tk.DISABLED)
disconnect_button.pack(side=tk.LEFT, padx=5)

play_button = tk.Button(button_frame, text="Play", command=start_playback, state=tk.DISABLED)
play_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(button_frame, text="Stop", command=stop_playback, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, padx=5)

create_track_button = tk.Button(button_frame, text="Create Track", command=create_track, state=tk.DISABLED)
create_track_button.pack(side=tk.LEFT, padx=5)

# Global variables
client = None

# Initial log message
log_message("FL Studio Connection Test started")
log_message("Click 'Connect' to connect to FL Studio")

# Start the GUI
root.mainloop()
