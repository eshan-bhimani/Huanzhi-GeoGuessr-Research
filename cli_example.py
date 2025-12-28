import threading
import sys
import queue
from toolset import view, navigation
from constants import google_api_key
from state_manager import state

def log_message(message: str):
    """Prints a message to the terminal."""
    print(message)

def init_env_cli() -> None:
    """
    Initializes a CLI-based environment for GeoGuessr research.
    Asks for user input from the terminal and saves panorama images.
    """
    print("--- GeoGuessr Research CLI Environment ---")
    print("Available functions: pan(angle), tilt(deg), zoom(rate), teleport(lat, lng), get_possible_pathways(), go_to_node(id)")
    print("Type 'exit' or 'quit' to close the environment.")

    # ------------------ Image Saving Logic ------------------
    def on_state_change(new_state):
        try:
            filepath = view.save_panorama(
                new_state['pano_id'], 
                new_state['width'], 
                new_state['height'], 
                new_state['latitude'], 
                new_state['longitude'], 
                new_state['heading'], 
                new_state['pitch'], 
                new_state['fov'], 
                google_api_key
            )
            log_message(f"Panorama saved to: {filepath}")
        except Exception as e:
            log_message(f"Error saving panorama: {e}")

    state.add_observer(on_state_change)

    # Initial save
    on_state_change(state.get_state())

    # ------------------ Command Processor (Background Thread) ------------------
    # Handles commands and keeps Playwright calls on a consistent thread.
    cmd_queue = queue.Queue()

    def command_worker():
        navigation.init_browser()
        
        while True:
            item = cmd_queue.get()
            if item is None: # Shutdown signal
                navigation.close_browser()
                break
            
            cmd_string, context = item
            try:
                # Simplistic eval for research environment
                result = eval(cmd_string, {"__builtins__": None}, context)
                log_message(f"Result: {result}")
            except Exception as e:
                log_message(f"Error: {e}")
            cmd_queue.task_done()

    # Start the worker thread
    worker_thread = threading.Thread(target=command_worker, daemon=True)
    worker_thread.start()

    # ------------------ CLI Loop ------------------
    context = {
        "pan": navigation.pan,
        "tilt": navigation.tilt, 
        "zoom": navigation.zoom,
        "get_possible_pathways": navigation.get_possible_pathways,
        "go_to_node": navigation.go_to_node,
        "teleport": navigation.teleport
    }

    try:
        while True:
            cmd = input("\n>>> ").strip()
            
            if not cmd:
                continue

            if cmd.lower() in ["exit", "quit"]:
                log_message("Exiting...")
                cmd_queue.put(None)
                break

            # Put the command into the queue for the worker thread
            cmd_queue.put((cmd, context))
            
            # Briefly wait for the worker to finish the command to keep input/output somewhat ordered
            # We don't join here because we want to allow new input if a command hangs,
            # but a small gap helps UI flow.
            # cmd_queue.join() # This would block the main thread until the worker finishes. 
            # Better to just let it run asynchronously.

    except KeyboardInterrupt:
        log_message("\nInterrupted. Exiting...")
        cmd_queue.put(None)

    # Wait for worker thread to finish cleanup
    worker_thread.join(timeout=5)

if __name__ == "__main__":
    init_env_cli()
