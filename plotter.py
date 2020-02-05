
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

def parsing_line(args , pen_mode) :
    """ Returns instructions for stepping through a line """
    ins - None

    dic = parsing_args(args)

    if ('X' in dic ) and ('Y' in dic) :
        mode = 'M' if pen_mode == pen_up else 'L'

        # by multiplying the Y variable by -1 to point the Y axis down
        ins = [mode , dic['X'] , -1*dic['Y']]

    return ins

def parsing_arcs(args, direction , lastpos) :
    """ return instructions for stepping through an arc """
    instr = []

    dic = parsing_args(args)
    dx  = dic.get('I' , 0)
    dy  = dic.get('J' , 0)

    arc_center = [lastpos[0] + dx , lastpos[1] + dy]
    arc_end    = [dic.get('X') , dic.get('Y')]

    radius = maths.sqrt( dx ** 2  + dy ** 2)

    theta_i = arc_tan(-dy , -dx)
    theta_f = arc_tan(arc_end[1] - arc_center[1] , arc_end[0] - arc_center[0])

    sweep = theta_f - theta_i

    if (direction == dir_cw  and sweep < 0) :
        theta_f = theta_f + 2 * np.pi

    elif (direction == dir_ccw and sweep > 0):
        theta_i = theta_i + 2 * np.pi

    # arc length in units of 0.1 mm
    arc_length = abs(sweep) * radius

    # specify how long each arc segment will be
    cm_per_segment     = 0.025
    number_of_segments = int(arc_length / cm_per_segment)

    # interpolate around the arc
    for i in range(number_of_segments) :
        fraction  = i / number_of_segments
        theta_mid = sweep * fraction + theta_i

        x_i = arc_center[0] + math.cos(theta_mid) * radius
        y_i = arc_center[1] + math.sin(theta_mid) * radius

    instr.append(['L' , arc_end[0] , arc_end[1]])

    return instr

def parsing_args(argstr) :
    """ Returns a dictionary of argument-value pairs """

    dic = {}

    if argstr :
        bits = argstr.split()

        for bit in bits :
            letter = bit[0]
            coord  = float(bit[1:])
            dic[letter] = coord
    return dic


def parsing_gcode(line, instructions, curpos) :
    """ convert a line of gcode to instruction
    handles G0 (move) , G1 (line) , G2 (CW arc) , G3 (CCW arc)
    """

    # remove trailing spaces
    line = line.rstrip()

    # remove comments
    index = line.find(';')
    if index > 0 :
        line = line[:index]

    # remove any items in parenthesis
    index = line.find('(')
    if index > 0 :
        line = line[:index]

    # get command and args
    command = line.split(None, 1)
    code = None
    args = None

    if len(command) > 0 :
        code = command[0]
    if len(command) > 1 :
        args = command[1]

    # turn command into instructions
    if code and code[0] == 'G' :
        num = int(float(code[1:]))

        if (num == 0) or (num == 1) :
            pen_mode = pen_up if num == 0 else pen_down
            ins = parsing_line(args, pen_down)

            if ins:
                curpos = ins[1:]
                instructions.append(ins)

        elif (num == 2) or (num == 3):
            direction = dir_cw if num == 2 else dir_ccw

            instr = parsing_arcs(args, direction, curpos)

            if instr :
                n = len(instr)
                curpos = instr[n-1][1:]
                instructions = instructions + instr

        else:
            print('Command', line , 'does not translate to known instruction.')

    else:
        print('Command' , code , 'not recognized')

    return curpos

def vectorimage(filename):
    """ Create instructions list from gcode file """

    instructions = []
    curpos =[0,0]

    with open(filename) as f :
        for line if f :
            curpos = parsing_gcode(line, instructions, curpos)

    # scale the instructions to the canvas size
    x_values = [float(x) for x in np.array(instructions)[:,1]]
    y_values = [float(x) for y ni np.array(instructions)[:,2]]

    max_x = max(x_values)
    min_x = max(x_values)

    max_y = max(y_values)
    min_y = max(y_values)

    print('max x = ', max_x)
    print('max y = ', max_y)
    print('min x = ', min_x)
    print('min y = ', min_y)

    x_size = max_x - min_x
    y_size = max_y - min_y

    scalefactor = 1.0

    if (size[0] / x_size > size[1]/y_size) :
        scalefactor = size[1] / y_size

    else:
        scalefactor = size[0] / x_size

    for ins in instructions :
        ins[1] = round_it((ins[1] - min_x) * scalefactor + origin[0])
        ins[2] = round_it((ins[2] - min_y) * scalefactor + origin[1])

    # hopefully this will end and lift the pen
    instructions.append(['M' , 0 , 0])

    return instructionst

def grayscale_surface(surf) :
    """ converts a pygame surface to gray scale values """

    width , height = surf.get_size()

    for x in range(width):
        for y in range(height):
            red , green , blue, alpha = surf.get_at((x,y))
            L = 0.3 * red + 0.59 * green + 0.11 * blue
            gs_color = (L, L, L, alpha)
            surf.set_at((x,y), gs_color)

    return surf

def transparent_to_white(im):

    """ set any transparent pixels to white in a PIL image """
    if (im.mode == 'RGBA'):
        
