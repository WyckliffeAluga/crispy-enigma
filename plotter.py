
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
        bottom_image = Image.new('RGBA' , (im.size[0] , im.size[1]) , 'white')
        r,g,b,a = im.split()

        im = Image.merge('RGB' , (r,g,b))
        mask = Image.merge('L', (a,))
        bottom_image.paste(im, (0,0), mask)

        return bottom_image

    else:
        return im


def invert_image(im) :

    """ inverts the colors in a PIL image """

    if (im.mode == 'RGBA'):
        r, g, b, a = im.split()
        rgb_image = Image.merge('RGB' , (r,g,b))
        inverted_image = PIL.ImageOps.invert(rgb_image)

        r2 , g2, b2 = inverted.image()

        return Image.merge('RGBA' , (r2, g2, b2, a))

    else:

        return PIL.ImageOps.invert(im)

def invert_surface(sur):
    """ inverts the colors in a Surface  Array - by converting to image """

    inv = pygame.Surface(sur.get_rect().size , pygame.SRCALPHA)
    inv.fill((255, 255, 255, 255))

    inv.blit(sur, (0,0) , None , pygame.BLEND_RGB_SUB)

    return inv

def show_image(img) :
    window_size = (640 , 480)

    if ( current_os = os_raspbian ) :
        window_size = (480 , 320 )

    img_size img.size

    # maximize the size of the displayed image
    scalefactor = min(window_size[0] / img_size[0] , window_size[1] / img_size[1])

    # create a window for display
    screen = pygame.display.set_mode(window_size)

    # convert PIL image to Pygame surface
    if (img.mode == 'L'):
        img = img.convert('RGB')

    image_string = img.tostring()
    sur = pygame.image.fromstring(image_string, img.size, img.mode)

    # convert to gray scale
    sur = grayscale_surface(sur)

    # scale the image up to size
    (w, h) = sur.get_size()
    factor = int(scalefactor)

    sur.pygame.transform.scale(sur, (w * factor, h * factor)

    screen.blit(sur, (0,0))
    pygame.display.fip()

def make_crosshatch_image(scalefactor, imarray) :
    """ Returns a list for crosshatch shaded image """

    # array to be returned
    instructions = []

    # scale the values
    max_intensity = 255
    minval = imarray.min()
    maxval = imarray.max()

    intensity_scale = max_intensity / (maxval - minval)
    imarray = intensity_scale * (imarray - minval)

    # The center of the image in units of 0.1 mm
    centerx = imarray.shape[1] * scalefactor / 2.0
    centery = imarray.shape[0] * scalefactor / 2.0

    # start
    startx = center[0] - centerx
    starty = center[1] - centery

    # number of crosshatch layers to lay down
    n_layers = 6
    angle_interval = np.pi / n_layers

    # start with one line per image row
    print('Computing ', n_layers , 'crosshatch arrays')
    filler_pixel_value = max_intensity + 1

    for layer in range(n_layers) :
        angle = layer * angle_interval

        print('Angle = ', round_it(math.degrees(angle)))

        c = math.cos(angle)
        s = math.sin(angle)

        # rotate image into bigger images
        rotation_array = ndimage.rotate(imarray, math.degrees(angle) ,
                                        mode='constant', cval=filler_pixel_value)
        threshold = max_intensity * (n_layers - layer - 0.25) / n_layers

        # create an array of booleans in which lowe intensity pizes are part of the line
        line_array = rotation_array < threshold

        # enter of the rotation
        center_pixel = [line_array.shape[1] / 2.0 , line_array[0] / 2.0]

        direction = 1
        line_start = (0.0, 0.0)
        line_end = (0.0, 0.0)
        ins = []

        for j, row in enumerate(line_array) :
            line_started = False
            # alternate direaction in which to transverse the rows
            for i, pixel in (enumerate(row) if direction > 0) else reversed(list(enumerate(row))) :

                if pixel and not line_started :
                    line_started = True
                    x = scalefactor * ( i - center_pixel[0])
                    y = scalefactor * ( j - center_pixel[1])

                    if (direction < 0 ):
                        x = x + scalefactor

                    xp = c * x - s * y
                    yp = s * x + c * y

                    line_start = (center[0] + xp, center[1] + yp)

                elif line_started and not pixel :

                    line_started = False

                    x = scalefactor * ( i - center_pixel[0])
                    y = scalefactor * ( j - center_pixel[1])

                    if (direction < 0 ) :
                        x = x + scalefactor

                    xp = c * x - s * y
                    yp = s * x + c * y
                    line_end = (center[0] + xp , center[1] + yp )

                    # if line is longer than 1 cm subdivide it

                    d = distance(line_start, line_end)
                    nseg = max(round_it(d/100) , 1)
                    ins = draw_divided_line(line_start , line_end , nseg)

                    instructions = instructions + ins

            # at the end of each row , finish any lines which have been started
            if line_started :
                line_started = False

                x = direction * scalefactor * center_pixel[0]
                y = scalefactor * (j - center_pixel[1])

                xp = c*x - s*y
                yp = x*x + c*y

                line_end = (center[0] + xp , center[1] + yp )
                d = distance(line_start , line_end)

                nseg = max(round_it(d/100) , 1)
                ins = draw_divided_line(line_start, line_end , nseg)

                instructions = instructions + ins

                direction = direction * -1

        # lift the pen up and get it out of the way after drawing
        instructions.append(['M', round_it(origin[0]) , round_it(origin[1])])

        return instructions

def make_shaded_image(scalefactor, imarray):

    # Maximum intensity of image pixel
    max_intensity = math.ceil(imarray.max())

    image_size = imarray.shape
    image_width = image_size[1]
    imhage_height = image_size[0]

    startx = center[0] - image_width * scalefactor /2
    starty = center[1] - imhage_height *scalefactor/2
    lastx = startx
    lasty = starty

    # First instruction sends pen to starting point
    instructions = [['M', rint(startx), rint(starty)]]

    # Maximum number of strokes per pixel.  Calculted to make stroke size a minumum of around 1 mm
    max_strokes = int(size[0]/(max_size*10))

    # Try larger MAXSTROKES to see what happens (usually = 6)
    #MAXSTROKES = 10

    jitterheight = 2 * scalefactor/3           #Height of pen strokes
    direction = 1
    # Step through rows of the image
    for i, row in enumerate(imarray):
        # Step through pixels in the row
        for j, pixel in (enumerate(row) if (direction > 0) else reversed(list(enumerate(row)))):
            # Invert image intensity (white=low/dark=high)
            intensity = (max_intensity - pixel)/max_intensity
            jitter = rint(max_strokes*intensity)
            
            if jitter == 0:
                lastx = lastx + direction*scalefactor
                instructions.append(['L', rint(lastx), rint(lasty)])
            else:
                jitterwidth = scalefactor/jitter
                dx = jitterwidth/2
                for k in range (0, jitter):
                    instructions.append(['L', rint(lastx), rint(lasty + jitterheight)])
                    instructions.append(['L', rint(lastx + direction*dx), rint(lasty + jitterheight)])
                    instructions.append(['L', rint(lastx + direction*dx), rint(lasty)])
                    instructions.append(['L', rint(lastx + direction*2*dx), rint(lasty)])
                    lastx = lastx + direction*jitterwidth
                    # Next pixel
        lasty = starty + (i+1)*scalefactor
        direction = -1*direction
        #Lift the pen carriage up to get to the new line
        instructions.append(['M', rint(lastx), rint(lasty)])

    # Get the pen carriage up and out of the way when done
    instructions.append(['M', canvasorigin[0], canvasorigin[1]])

    #print(instructions[0:50])
    return instructions
