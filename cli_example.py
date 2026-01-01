import threading
import sys
import queue
from toolset.instance import StreetViewInstance

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

    # ------------------ Command Processor (Background Thread) ------------------
    # Handles commands and keeps Playwright calls on a consistent thread.
    cmd_queue = queue.Queue()

    def command_worker():
        # Using StreetViewInstance to manage state and browser interaction
        instance = StreetViewInstance()
        log_message("StreetViewInstance initialized.")
        
        # Initial save
        try:
            filepath = instance.save_panorama()
            log_message(f"Initial panorama saved to: {filepath}")
        except Exception as e:
            log_message(f"Error saving initial panorama: {e}")

        # Context for the commands, using instance methods
        context = {
            "pan": instance.pan,
            "tilt": instance.tilt, 
            "zoom": instance.zoom,
            "get_possible_pathways": instance.get_possible_pathways,
            "go_to_node": instance.go_to_node,
            "teleport": instance.teleport,
            "save_panorama": instance.save_panorama,
            "get_state": instance.get_state
        }
        
        while True:
            item = cmd_queue.get()
            if item is None: # Shutdown signal
                instance.close()
                break
            
            cmd_string = item
            try:
                # Simplistic eval for research environment
                result = eval(cmd_string, {"__builtins__": None}, context)
                log_message(f"Result: {result}")
                
                # Auto-call save_panorama after every function call
                try:
                    filepath = instance.save_panorama()
                    log_message(f"Auto-saved panorama: {filepath}")
                except Exception as e:
                    log_message(f"Error in auto-save: {e}")
                    
            except Exception as e:
                log_message(f"Error: {e}")
            cmd_queue.task_done()

    # Start the worker thread
    worker_thread = threading.Thread(target=command_worker, daemon=True)
    worker_thread.start()

    # ------------------ CLI Loop ------------------
    try:
        while True:
            cmd = input("\n>>> ").strip()
            
            if not cmd:
                continue

            if cmd.lower() in ["exit", "quit"]:
                log_message("Exiting...")
                cmd_queue.put(None)
                break

            # Put the command string into the queue
            cmd_queue.put(cmd)
            
            # We don't wait for completion here to allow the CLI to stay responsive
            # and to handle potential interruptions properly.

    except KeyboardInterrupt:
        log_message("\nInterrupted. Exiting...")
        cmd_queue.put(None)

    # Wait for worker thread to finish cleanup
    worker_thread.join(timeout=5)

if __name__ == "__main__":
    init_env_cli()
