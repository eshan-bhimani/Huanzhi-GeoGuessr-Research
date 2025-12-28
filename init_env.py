from PIL import Image, ImageTk
import io
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import sys
from toolset import view, navigation
from constants import google_api_key
from state_manager import state

def init_env() -> None:
    """
    Initializes the gui window that shows the current view of the panorama.
    Includes an integrated terminal for command input and logging.

    Args:
        None

    Returns:
        None
    """ 
    # Remove direct init_browser call from main thread
    # navigation.init_browser() 

    # Initialize basic TK window
    root = tk.Tk()
    root.title("Huanzhi GeoGuessr Research Environment")
    
    # ------------------ Layout Configuration ------------------
    # Frame for the Panorama View (Top)
    view_frame = tk.Frame(root)
    view_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Label for Image
    label = tk.Label(view_frame)
    label.pack()

    # Frame for the Terminal (Bottom)
    terminal_frame = tk.Frame(root, height=200)
    terminal_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    # Terminal Output Area (ScrolledText)
    terminal_output = ScrolledText(terminal_frame, height=10, state='disabled', bg='black', fg='white', font=("Consolas", 10))
    terminal_output.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Terminal Input Area (Entry)
    terminal_input = tk.Entry(terminal_frame, bg='black', fg='white', insertbackground='white', font=("Consolas", 10))
    terminal_input.pack(side=tk.BOTTOM, fill=tk.X)
    terminal_input.focus_set()

    # ------------------ Logging & Output ------------------
    def log_message(message: str):
        """Appends a message to the terminal output widget."""
        terminal_output.configure(state='normal')
        terminal_output.insert(tk.END, str(message) + "\n")
        terminal_output.see(tk.END)
        terminal_output.configure(state='disabled')

    # Redirecting helper for key bindings
    def log_and_execute(func, *args):
        try:
            result = func(*args)
            log_message(result)
        except Exception as e:
            log_message(f"Error: {e}")

    # ------------------ View Update Logic ------------------
    def update_view(current_state):
        try:
            view.show_panorama(
                current_state['width'], 
                current_state['height'], 
                current_state['latitude'], 
                current_state['longitude'], 
                current_state['heading'], 
                current_state['pitch'], 
                current_state['fov'], 
                google_api_key, 
                label
            )
        except Exception as e:
            log_message(f"Error updating view: {e}")

    # Observer for state changes
    def on_state_change(new_state):
        # Schedule update on main thread
        root.after(0, update_view, new_state)

    state.add_observer(on_state_change)

    # Initial render
    update_view(state.get_state())

    # ------------------ Key Bindings ------------------
    # Key bindings calling navigation toolset and logging to GUI terminal
    root.bind("<Right>", lambda e: log_and_execute(navigation.pan, 15))
    root.bind("<Left>", lambda e: log_and_execute(navigation.pan, -15))
    root.bind("<Up>", lambda e: log_and_execute(navigation.tilt, 10)) 
    root.bind("<Down>", lambda e: log_and_execute(navigation.tilt, -10)) 
    root.bind("w", lambda e: log_and_execute(navigation.tilt, 10))
    root.bind("s", lambda e: log_and_execute(navigation.tilt, -10))
    root.bind("a", lambda e: log_and_execute(navigation.pan, -15))
    root.bind("d", lambda e: log_and_execute(navigation.pan, 15))
    root.bind("q", lambda e: log_and_execute(navigation.zoom, 0.8)) 
    root.bind("e", lambda e: log_and_execute(navigation.zoom, 1.2))

    # ------------------ Command Processor (Background Thread) ------------------
    # This queue handles commands that should run in the background to avoid freezing the GUI
    # and keeps Playwright calls on a consistent thread.
    cmd_queue = queue.Queue()

    def command_worker():
        # Playwright MUST be initialized in the thread where it is used.
        navigation.init_browser()
        
        while True:
            item = cmd_queue.get()
            if item is None: # Shutdown signal
                navigation.close_browser()
                break
            
            cmd_string, context, callback = item
            try:
                # Simplistic eval for demonstration/research environment
                result = eval(cmd_string, {"__builtins__": None}, context)
                # Helper to flush output to the GUI in a thread-safe way
                root.after(0, callback, result)
            except Exception as e:
                 root.after(0, callback, f"Error: {e}")
            cmd_queue.task_done()

    # Start the worker thread
    threading.Thread(target=command_worker, daemon=True).start()

    # ------------------ Terminal Command Execution ------------------
    def handle_command(event=None):
        cmd = terminal_input.get()
        terminal_input.delete(0, tk.END)
        
        if not cmd.strip():
            return

        log_message(f">>> {cmd}")

        if cmd.strip().lower() in ["exit", "quit"]:
            cmd_queue.put(None) # Signal worker to close browser
            root.quit()
            return

        # Execute command in a context with navigation tools
        context = {
            "pan": navigation.pan,
            "tilt": navigation.tilt, 
            "zoom": navigation.zoom,
            "get_possible_pathways": navigation.get_possible_pathways,
            "go_to_node": navigation.go_to_node,
            "teleport": navigation.teleport
        }

        # Put the command into the queue for the worker thread
        cmd_queue.put((cmd, context, log_message))

    terminal_input.bind("<Return>", handle_command)

    # Initial welcome message
    log_message("--- Command Interface ---")
    log_message("Available functions: pan(angle), tilt(deg), zoom(rate), teleport(lat, lng), get_possible_pathways(), go_to_node(id)")
    log_message("Enter commands below:")

    def on_closing():
        cmd_queue.put(None) # Shutdown worker thread and close browser
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start GUI loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        cmd_queue.put(None)
        print("Exiting...")

if __name__ == "__main__":
    init_env()