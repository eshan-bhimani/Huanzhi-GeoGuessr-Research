from PIL import Image, ImageTk
import io
import tkinter as tk
import numpy as np
import requests
from toolset import view
from constants import google_api_key

def init_env() -> None:
    """
    Initializes the gui window that shows the current view of the panorama.

    Args:
        None

    Returns:
        None
    """ 
    #Place holder values
    width = 600
    height = 300
    latitude = 46.414382
    longitude = 10.013988
    heading = 151.78
    pitch = -0.76
    fov = 90

    api_key = google_api_key
    response = requests.get(f"https://maps.googleapis.com/maps/api/streetview?size={width}x{height}&location={latitude},{longitude}&heading={heading}&pitch={pitch}&fov={fov}&key={api_key}")
    
    #create the tkinter window **Must call before declaring tk_img variable
    root = tk.Tk()

    #from the response content of the api call, convert to bytesio, making an accessible reference to the image
    img = Image.open(io.BytesIO(response.content))
    #convert to tkimg format
    tk_img = ImageTk.PhotoImage(img)

    # Create the Label widget to display the tk_img
    #Gotta initialize the image so it knows to draw an image first
    label = tk.Label(root, image=tk_img)
    label.image = tk_img # type: ignore
    label.pack()
    
    
    def turn_right(event):
        nonlocal heading
        heading += 15
        heading %= 360
        print(f"heading = {heading}")
        view.show_panorama(width, height, latitude, longitude, heading, pitch, fov, api_key, label)
        print('right')

    def turn_left(event):
        nonlocal heading
        heading -= 15
        heading %= 360
        print(f"heading = {heading}")
        view.show_panorama(width, height, latitude, longitude, heading, pitch, fov, api_key, label)
        print('left')

    def turn_up(event):
        nonlocal pitch
        pitch += 10
        if pitch >= 90:
            pitch = 90
        print(f"pitch = {pitch}")
        view.show_panorama(width, height, latitude, longitude, heading, pitch, fov, api_key, label)
        print('up')

    def turn_down(event):
        nonlocal pitch
        pitch -= 10
        if pitch <= -90:
            pitch = -90
        print(f"pitch = {pitch}")
        view.show_panorama(width, height, latitude, longitude, heading, pitch, fov, api_key, label)
        print('down')

    def zoom_out(event):
        nonlocal fov
        fov += 10
        if fov >= 120:
            fov = 120
        print(f"fov = {fov}")
        view.show_panorama(width, height, latitude, longitude, heading, pitch, fov, api_key, label)
        print('zoom out')

    def zoom_in(event):
        nonlocal fov
        fov -= 10
        if fov <= 0:
            fov = 0
        print(f"fov = {fov}")
        view.show_panorama(width, height, latitude, longitude, heading, pitch, fov, api_key, label)
        print('zoom in')


    root.bind("<Right>", turn_right)
    root.bind("<Left>", turn_left)
    root.bind("<Up>", turn_up)
    root.bind("<Down>", turn_down)
    root.bind("q", zoom_out)
    root.bind("e", zoom_in)

    root.mainloop()

init_env()