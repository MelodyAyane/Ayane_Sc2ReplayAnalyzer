import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser
import ttkbootstrap
import sc2reader
import os
import sys
import psutil
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

    if isinstance(event, sc2reader.events.tracker.UnitBornEvent) and event.control_pid == player.pid:
        if event.second not in build_order:  # Check if this second is already in the build order
            build_order[event.second] = {"population": 0, "units": defaultdict(int), "buildings": [],
                                         "upgrades": []}  # If not, initialize it
        build_order[event.second]["units"][event.unit_type_name] += 1

    if isinstance(event, sc2reader.events.tracker.PlayerStatsEvent) and event.pid == player.pid:
        current_supply = event.food_used  # Update the current supply count

    if isinstance(event, sc2reader.events.tracker.UnitBornEvent) and event.control_pid == player.pid:
        if event.second not in build_order:  # Check if this second is already in the build order
            build_order[event.second] = {"population": 0, "units": defaultdict(int), "buildings": [], "upgrades": []}  # If not, initialize it
        build_order[event.second]["units"][event.unit_type_name] += 1
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
    # Use player.name to get the player's name
    player_name = player.name
    text_widgets['Build Order'].insert(tk.END, f"\nPlayer ", "bold_large")
    text_widgets['Build Order'].insert(tk.END, f"{player_name}'s build order:\n", "bold_large")
    for second in sorted(build_order.keys()):
        if second == 0:  # Skip the 0 second time point
            continue
        if second == min(build_order.keys()):  # Special case for the first time point
            text_widgets['Build Order'].insert(tk.END, f"At {second}s (Population: {build_order[second]['population']}):\n")
        elif build_order[second]["upgrades"] or build_order[second]["buildings"]:  # Only print the population count if there are upgrades or buildings
            text_widgets['Build Order'].insert(tk.END, f"At {second}s (Population: {build_order[second]['population']}):\n")
        for unit, count in build_order[second]["units"].items():
            if unit not in ['Interceptor', 'Larva', 'Broodling']:  # Skip printing if the unit is 'Interceptor', 'Larva' or 'Broodling'
                text_widgets['Build Order'].insert(tk.END, f"    {unit} *{count} was built\n")
        for building in build_order[second]["buildings"]:
            text_widgets['Build Order'].insert(tk.END, f"    {building} was built\n")
        for upgrade in build_order[second]["upgrades"]:
            text_widgets['Build Order'].insert(tk.END, f"    {upgrade} was completed\n")
    text_widgets['Build Order'].insert(tk.END, "\n")  # Add an empty line after each player's build order

def analyze_replay():
    """Analyzes a StarCraft II replay."""
    root = tk.Tk()  # Create a standard Tk instance

    def close_window():
        # Get current process using psutil
        parent = psutil.Process(os.getpid())
        # Iterate over the all the running process
        for child in parent.children(recursive=True):
            child.terminate()  # Terminate process

        root.quit()  # End the mainloop
        root.destroy()  # Destroy the root window
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
    info_tabs = ['Basic Info', 'Player Info', 'Build Order', 'Game Timeline', 'Game Statistics', 'Chat Messages', 'Macro analysis']
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

    # Print player info
    sys.stdout = TextRedirector(text_widgets['Player Info'])
    players_info = []
    button_frame = tk.Frame(text_widgets['Player Info'])  # Create a new frame to contain the buttons
    button_frame.pack(side=tk.BOTTOM)  # Place the frame at the bottom of the window
    # Create a set to store the names of players that have been processed
    processed_players = set()

    for player in replay.players:
        # Skip this player if their information has already been added
        if player.name in processed_players:
            continue

        player_stats = {'apm': None, 'epm': None}  # Initialize player stats
        build_order = defaultdict(lambda: {"population": 0, "units": defaultdict(int), "buildings": [],
                                           "upgrades": []})  # A dictionary to store the build order for each time point
        current_supply = 0  # Variable to store the current supply count
        action_count = 0
        effective_action_count = 0
        last_action = None
        for event in replay.events:
            if isinstance(event, sc2reader.events.game.CommandEvent) and event.player == player:
                action_count += 1
                if last_action != event.ability_name:
                    effective_action_count += 1
                last_action = event.ability_name

        game_length_minutes = replay.game_length.seconds / 60
        player_stats['apm'] = int(action_count / game_length_minutes)
        player_stats['epm'] = int(effective_action_count / game_length_minutes)  # Only count distinct actions

        players_info.append(
            f"\nPlayer name: {player.name}\nPlayer race: {player.play_race}\nPlayer color: {player.color}\nAverage APM: {player_stats['apm']}\nAverage EPM: {player_stats['epm']}")  # Add player color and info

        # Add this player's name to the set of processed players
        processed_players.add(player.name)

    players_info_str = '\n'.join(players_info)  # Convert the list to a string

    # Print the player info
    sys.stdout = TextRedirector(text_widgets['Player Info'])
    text_widgets['Player Info'].tag_configure("bold_large", font=('Microsoft YaHei', 14, 'bold'))
    text_widgets['Player Info'].delete('1.0', tk.END)  # Clear the text widget before inserting new text
    text_widgets['Player Info'].insert(tk.END, players_info_str, "bold_large")
    # Add an entry for the 0 second time point
    build_order[0]["units"]['SCV'] += 1
    build_order[0]["population"] = 1

    # Create a build_order dictionary for each player
    build_orders = {player: defaultdict(lambda: {"population": 0, "units": defaultdict(int), "buildings": [], "upgrades": []}) for player in replay.players}
    current_supplies = {player: 0 for player in replay.players}  # Variable to store the current supply count for each player

    for event in replay.events:
        for player in replay.players:
            build_orders[player], current_supplies[player] = handle_event(event, build_orders[player], current_supplies[player], player)

    for player in replay.players:
        print_build_order(text_widgets, replay, player, build_orders[player])

    # Print game timeline
    sys.stdout = TextRedirector(text_widgets['Game Timeline'])
    print(f"Game length (seconds): {replay.length.seconds}")
    print(f"Game length (game time): {replay.game_length.seconds}")

    # Print game statistics
    sys.stdout = TextRedirector(text_widgets['Game Statistics'])
    for player in replay.players:
        total_units = 0
        total_killed_units = 0
        total_destroyed_buildings = 0
        total_unspent_resources = 0
        total_supply_capped_time = 0
        previous_event = None
        for event in replay.events:
            if isinstance(event, sc2reader.events.tracker.UnitBornEvent) and event.control_pid == player.pid:
                total_units += 1
            elif isinstance(event, sc2reader.events.tracker.UnitDiedEvent) and event.killing_player_id == player.pid:
                if event.unit.is_building:
                    total_destroyed_buildings += 1
                else:
                    total_killed_units += 1
            elif isinstance(event, sc2reader.events.tracker.PlayerStatsEvent) and event.pid == player.pid:
                total_unspent_resources += event.minerals_current + event.vespene_current
                if previous_event and event.food_used == event.food_made:
                    total_supply_capped_time += event.second - previous_event.second
                previous_event = event
        average_unspent_resources = int(total_unspent_resources / replay.game_length.seconds)
        print(
            f"Player {player.name} created {total_units} units, killed {total_killed_units} units, and destroyed {total_destroyed_buildings} buildings")
        print(
            f"Player {player.name} had an average of {average_unspent_resources} unspent resources and was supply capped for {total_supply_capped_time} seconds")

    # Print chat messages
    sys.stdout = TextRedirector(text_widgets['Chat Messages'])
    if replay.messages:
        for message in replay.messages:
            print(f"{message.player.name}: {message.text}")
    else:
        print("No chat messages in this replay.")

    # Print macro analysis
    sys.stdout = TextRedirector(text_widgets['Macro analysis'])
    for player in replay.players:
        total_units_produced = 0
        total_buildings_produced = 0
        total_upgrades_completed = 0
        for event in replay.events:
            if isinstance(event, sc2reader.events.tracker.UnitBornEvent) and event.control_pid == player.pid:
                total_units_produced += 1
            elif isinstance(event, sc2reader.events.tracker.UnitInitEvent) and event.control_pid == player.pid:
                total_buildings_produced += 1
            elif isinstance(event, sc2reader.events.tracker.UpgradeCompleteEvent) and event.pid == player.pid:
                total_upgrades_completed += 1
        units_produced_rate = total_units_produced / replay.game_length.seconds
        buildings_produced_rate = total_buildings_produced / replay.game_length.seconds
        upgrades_completed_rate = total_upgrades_completed / replay.game_length.seconds
        print(f"Player {player.name} produced units at a rate of {units_produced_rate} per second")
        print(f"Player {player.name} produced buildings at a rate of {buildings_produced_rate} per second")
        print(f"Player {player.name} completed upgrades at a rate of {upgrades_completed_rate} per second")


    # Print metadata in Basic Info tab
    sys.stdout = TextRedirector(text_widgets['Basic Info'])
    print(f"Replay created at: {replay.date}")
    print(f"Replay file size: {os.path.getsize(replay_file)} bytes")

    root.mainloop()  # Move this line to the end of the function

if __name__ == "__main__":
    analyze_replay()