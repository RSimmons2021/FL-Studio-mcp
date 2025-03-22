# FL Studio MCP Installation Guide

This guide explains how to install and use the FL Studio MCP (MIDI Control Protocol) script to enable communication between FL Studio and external applications.

## Installation Steps

### 1. Install the MIDI Script in FL Studio

1. Locate your FL Studio installation directory
   - Typically: `C:\Program Files\Image-Line\FL Studio 20`
   - Or in your user directory: `%USERPROFILE%\Documents\Image-Line\FL Studio`

2. Find the MIDI scripts folder:
   - Look for: `Shared\Python\Lib\site-packages\flmcp`
   - If it doesn't exist, create it

3. Copy the entire `FlStudioMCP_Remote_Script` folder to the MIDI scripts directory:
   ```
   flmcp/
   └── FlStudioMCP_Remote_Script/
       ├── __init__.py
       ├── create_track.py
       ├── fl_studio_prompt.py
       └── [other files]
   ```

### 2. Configure FL Studio to Use the Script

1. Open FL Studio
2. Go to Options > MIDI Settings
3. In the "Controller type" dropdown, select "FlStudioMCP_Remote_Script"
4. Make sure the script is enabled

### 3. Using the Client Application

Once the script is loaded in FL Studio, you can use the client application to send commands:

1. Run the client application:
   ```
   python FlStudioMCP_Remote_Script/fl_studio_prompt.py --gui
   ```

2. Enter prompts to create tracks, such as:
   - "Create a hip hop bass track"
   - "Make a trap beat with 808s"
   - "Create a melodic techno lead"

## Troubleshooting

### Script Not Found in FL Studio

- Make sure you've copied the script to the correct directory
- Restart FL Studio after copying the script

### Connection Issues

- Ensure FL Studio is running before starting the client
- Check that port 9050 is not being used by another application
- Look for error messages in the FL Studio log file at:
  `%USERPROFILE%\Documents\FL Studio\Logs\flstudio_mcp.log`

### Commands Not Working

- Make sure the script is properly loaded in FL Studio
- Check the log file for any error messages
- Verify that the client is connecting to the correct port (9050)

## How It Works

The FL Studio MCP script creates a server that listens for commands on port 9050. When FL Studio loads the script, it gains access to the FL Studio API, allowing it to create tracks, set parameters, and control playback.

The client application sends JSON-formatted commands to the server, which then executes them using the FL Studio API.
