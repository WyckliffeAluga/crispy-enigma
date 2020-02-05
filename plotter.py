
import serial

from PIL import Image
import numpy as np
from scipy import ndimage
import pygame
import tkinter
from tkinter import filedialog
import math

# canvas dimensions in 0.1 mm
origin = [2000 , 2700]
size   = [4000 , 3500]
center = [origin[0] + size[0] / 2 , origin[1] + size[1]/2]

# maximum pixels allowed per side
max_size   = 64
cmd_unkown = 0
cmd_ok     = 1
cmd_console= 2

pen_up  = 0
pen_down= 1

dir_cw  = 0
dir_ccw = 1

shaded_scalar_image     = 0
crosshatch_scalar_image = 1
svg_vector_image        = 2

os_windows = 0
os_raspbian= 1

# set current os to windows
current_os = os_windows

# make helper functions

def round_it(x):
    """ Returns rounded interger """
    return int(round(x))

def remove_return(str):
    """ Returns a string without the return clause"""
    return str.rstrip('\r\n')

def arctan(dy, dx):
    """ Returns the arctan of angle between 0 and 2*pi """
    arc_tan = math.atan2(dy, dx)

    if arc_tan < 0:
        arc_tan = arc_tan + 2 * np.pi

    return arc_tan


# process the commands received from arduino

def data(line):
    """  line data comes in binary - here we convert it to string"""

    line = line.decode('ascii')

    if line[0] == '#' :
        return cmd_console

    elif line.find('OK') ==  0:
        return cmd_ok

    else :
        return cmd_unkown
