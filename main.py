import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser
import ttkbootstrap
import sc2reader
import os
import sys
from collections import defaultdict

class TextRedirector(object):
    """Redirects standard output to a tkinter text widget."""
    def __init__(self, widget):
        self.widget = widget

    def write(self, str):
        self.widget.insert(tk.END, str)
        self.widget.see(tk.END)

    def flush(self):
        pass  # Required for file-like objects

def open_url(event):
    """Opens a URL in the default web browser."""
    webbrowser.open_new(event.widget.cget("text"))

def open_url(player_name):
    """Opens a URL in the default web browser."""
    webbrowser.open_new(f"https://nonapa.com/search?query={player_name}")

def handle_event(event, build_order, current_supply, player):
    """Handles a single event from the replay."""
    if isinstance(event, sc2reader.events.tracker.PlayerStatsEvent) and event.pid == player.pid:
        current_supply = event.food_used  # Update the current supply count
    elif isinstance(event, sc2reader.events.tracker.UnitBornEvent) and event.control_pid == player.pid:
        if event.second not in build_order:  # Check if this second is already in the build order
            build_order[event.second] = {"population": 0, "units": [], "buildings": [], "upgrades": []}  # If not, initialize it
        if event.second == 0:  # If this is the 0 second time point
            if 'SCV' in build_order[event.second]["units"]:  # If an SCV has already been added, skip this loop
                return build_order, current_supply
            else:  # If no SCV has been added yet, add one and update the population count
                build_order[event.second]["units"].append(event.unit_type_name)
                current_supply += 1  # Increase the worker count
                build_order[event.second]["population"] = current_supply  # Update the population count in the build order
                return build_order, current_supply
        build_order[event.second]["units"].append(event.unit_type_name)
        if event.unit_type_name in ['SCV', 'Probe', 'Drone']:  # Check if the unit is a worker
            current_supply += 1  # Increase the worker count
        build_order[event.second]["population"] = current_supply  # Update the population count in the build order
    elif isinstance(event, sc2reader.events.tracker.UpgradeCompleteEvent) and event.pid == player.pid and event.second != 0:
        build_order[event.second]["upgrades"].append(event.upgrade_type_name)
        build_order[event.second]["population"] = current_supply  # Update the population count in the build order
    elif isinstance(event, sc2reader.events.tracker.UnitInitEvent) and event.control_pid == player.pid and event.second != 0:
        build_order[event.second]["buildings"].append(event.unit_type_name)
        build_order[event.second]["population"] = current_supply  # Update the population count in the build order

    return build_order, current_supply

def print_build_order(text_widgets, replay, player, build_order):
    """Prints the build order for a single player."""
    text_widgets['Build Order'].tag_configure("bold_large", font=('Microsoft YaHei', 14, 'bold'))
    text_widgets['Build Order'].insert(tk.END, f"Player {player.name}'s build order:\n", "bold_large")
    for second in sorted(build_order.keys()):
        if second == 0:  # Skip the 0 second time point
            continue
        if second == min(build_order.keys()):  # Special case for the first time point
            text_widgets['Build Order'].insert(tk.END,
                                               f"At {second}s (Population: {build_order[second]['population']}):\n")
        elif build_order[second]["upgrades"] or build_order[second][
            "buildings"]:  # Only print the population count if there are upgrades or buildings
            text_widgets['Build Order'].insert(tk.END,
                                               f"At {second}s (Population: {build_order[second]['population']}):\n")
        for unit in build_order[second]["units"]:
            text_widgets['Build Order'].insert(tk.END, f"    {unit} was built\n")
        for building in build_order[second]["buildings"]:
            text_widgets['Build Order'].insert(tk.END, f"    {building} was built\n")
        for upgrade in build_order[second]["upgrades"]:
            text_widgets['Build Order'].insert(tk.END, f"    {upgrade} was completed\n")
        text_widgets['Build Order'].insert(tk.END, "\n")  # Add an empty line after each player's build order

def analyze_replay():
    """Analyzes a StarCraft II replay."""
    root = tk.Tk()  # Create a standard Tk instance

    def close_window():
        root.quit()
        root.destroy()
        os._exit(0)  # Forcefully exit the program

    root.protocol("WM_DELETE_WINDOW", close_window)  # Close the window when the close button is pressed
    style = ttkbootstrap.Style(theme="flatly")  # Apply a ttkbootstrap style

    root.overrideredirect(True)  # Hide the title bar
    root.withdraw()  # Hide the main window
    replay_file = filedialog.askopenfilename()  # Open the file dialog

    replay = sc2reader.load_replay(replay_file)

    # Create a new window to display the print statements
    output_window = tk.Toplevel(root)
    output_window.title('Replay Analysis')  # Set window title
    output_window.geometry('800x600')  # Set window size

    # Create a notebook (tabbed view)
    notebook = ttk.Notebook(output_window)
    notebook.pack(fill='both', expand=True)

    # Create a tab for each type of information
    info_tabs = ['Basic Info', 'Player Info', 'Build Order', 'Game Timeline', 'Game Statistics', 'Chat Messages', 'Metadata']
    text_widgets = {}
    for tab in info_tabs:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=tab)

        # Create a scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create a text box with custom appearance
        output_text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                              bg='black', fg='white', font=('Microsoft YaHei', 12))
        output_text.pack(fill=tk.BOTH, expand=True)
        # Connect the scrollbar to the text box
        scrollbar.config(command=output_text.yview)

        text_widgets[tab] = output_text

    # Print basic information about the replay
    sys.stdout = TextRedirector(text_widgets['Basic Info'])
    players_info = '\n'.join(
        f"{player}, Color: {player.color}" for player in replay.players)  # Add player color information
    print(f"Map: {replay.map_name}")
    print(f"Players:\n{players_info}")

    # Print game version and map information
    print(f"Game version: {replay.release_string}")

    sys.stdout = TextRedirector(text_widgets['Player Info'])
    players_info = []
    button_frame = tk.Frame(text_widgets['Player Info'])  # Create a new frame to contain the buttons
    button_frame.pack(side=tk.BOTTOM)  # Place the frame at the bottom of the window
    for player in replay.players:
        players_info.append(
            f"Player name: {player.name}\nPlayer race: {player.play_race}\nPlayer color: {player.color}")  # Add player color and info
        info_button = tk.Button(button_frame, text=player.name,  # Add the button to the frame
                                command=lambda player_name=player.name: open_url(player_name))
        info_button.pack(side=tk.LEFT,
                         padx=10)  # Place the button to the left of the previous button with a horizontal padding of 10 pixels
    players_info = '\n'.join(players_info)
    print(f"Players:\n{players_info}")

    # Print build order
    for player in replay.players:
        build_order = defaultdict(lambda: {"population": 0, "units": [], "buildings": [], "upgrades": []})  # A dictionary to store the build order for each time point
        current_supply = 0  # Variable to store the current supply count

        # Add an entry for the 0 second time point
        build_order[0]["units"].append('SCV')
        build_order[0]["population"] = 1

        for event in replay.events:
            build_order, current_supply = handle_event(event, build_order, current_supply, player)

        print_build_order(text_widgets, replay, player, build_order)

    # Print game timeline
    sys.stdout = TextRedirector(text_widgets['Game Timeline'])
    print(f"Game length (seconds): {replay.length.seconds}")
    print(f"Game length (game time): {replay.game_length.seconds}")

    # Print game statistics
    sys.stdout = TextRedirector(text_widgets['Game Statistics'])
    for player in replay.players:
        minerals_collected = 0
        vespene_collected = 0
        for event in replay.events:
            if isinstance(event, sc2reader.events.tracker.PlayerStatsEvent) and event.pid == player.pid:
                minerals_collected += event.minerals_collection_rate
                vespene_collected += event.vespene_collection_rate
        print(f"Player {player.name} collected {minerals_collected} minerals and {vespene_collected} vespene")

    # Print chat messages
    sys.stdout = TextRedirector(text_widgets['Chat Messages'])
    if replay.messages:
        for message in replay.messages:
            print(f"{message.player.name}: {message.text}")
    else:
        print("No chat messages in this replay.")
    # Print metadata
    sys.stdout = TextRedirector(text_widgets['Basic Info'])
    print(f"Replay created at: {replay.date}")
    print(f"Replay file size: {os.path.getsize(replay_file)} bytes")

    root.mainloop()  # Move this line to the end of the function

if __name__ == "__main__":
    analyze_replay()