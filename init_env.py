from PIL import Image, ImageTk
import io
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
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
    root.bind("q", lambda e: log_and_execute(navigation.zoom, 0.8)) 
    root.bind("e", lambda e: log_and_execute(navigation.zoom, 1.2))

    # ------------------ Terminal Command Execution ------------------
    def handle_command(event=None):
        cmd = terminal_input.get()
        terminal_input.delete(0, tk.END)
        
        if not cmd.strip():
            return

        log_message(f">>> {cmd}")

        if cmd.strip().lower() in ["exit", "quit"]:
            root.quit()
            return

        # Execute command in a context with navigation tools
        context = {
            "pan": navigation.pan,
            "tilt": navigation.tilt, 
            "zoom": navigation.zoom,
            "get_possible_pathways": navigation.get_possible_pathways,
            "go_to_node": navigation.go_to_node
        }

        def run_eval():
            try:
                # Simplistic eval for demonstration/research environment
                result = eval(cmd, {"__builtins__": None}, context)
                # Helper to flush output to the GUI in a thread-safe way
                root.after(0, log_message, result)
            except Exception as e:
                 root.after(0, log_message, f"Error: {e}")

        # Run eval in separate thread to prevent GUI freezing during network calls
        threading.Thread(target=run_eval, daemon=True).start()

    terminal_input.bind("<Return>", handle_command)

    # Initial welcome message
    log_message("--- Command Interface ---")
    log_message("Available functions: pan(angle), tilt(deg), zoom(rate), get_possible_pathways(), go_to_node(id)")
    log_message("Enter commands below:")

    # Start GUI loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    init_env()