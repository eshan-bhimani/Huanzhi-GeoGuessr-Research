# Necessary for toolset functions:
# Semantic Name (e.g. calculate_mortgage vs. calc_m)
# Type Hints (e.g. count: int)
# Docstring Logic (Explains what the tool does and when to use it)
# Docstring Args (Explains constraints [e.g., "Must be YYYY-MM-DD" or "Must be in USD"])

from typing import Union # Union is used to have tuples as a typecast for function arguments
import requests
from PIL import Image, ImageTk
import io

#Better to have the model not have access to the json including all of the information, maybe better to have the agents have a function calling for that information as it needs.
def show_panorama(width, height, latitude, longitude, heading, pitch, fov, api_key, label) -> None:
    """
    Shows the view of the panorama given the current configurations (heading, pitch, fov, location).
    
    Args:
        None
    
    Returns:
        None
    """

    #We only really need these first two lines, the others are just for the gui environment.
    response = requests.get(f"https://maps.googleapis.com/maps/api/streetview?size={width}x{height}&location={latitude},{longitude}&heading={heading}&pitch={pitch}&fov={fov}&key={api_key}")
    img = Image.open(io.BytesIO(response.content))

    #temporary, will get deleted once we interface with models
    tk_img = ImageTk.PhotoImage(img)
    label.configure(image=tk_img)
    label.image = tk_img


def set_heading(heading: float) -> None:
    """
    Turns the view to the specified heading. 
    
    Args:
        heading (float): The new camera compass direction in degrees.
    
    Returns:
        None
    """

    raise NotImplementedError()

def set_fov(fov: float) -> None:
    """
    Adjusts the fov, zooming into the given panorama.
    
    Args:
        fov (float): The new camera fov in degrees.
    
    Returns:
        None
    """

    raise NotImplementedError()

def set_pitch(pitch: float) -> None:
    """
    Adjusts the pitch, changing the up and down viewing angle.
    
    Args:
        pitch (float): The up and down viewing angle in degrees.

    Returns:
        None
    """

    raise NotImplementedError()