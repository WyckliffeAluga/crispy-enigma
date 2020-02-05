
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
        for line in f :
            curpos = parsing_gcode(line, instructions, curpos)

    # scale the instructions to the canvas size
    x_values = [float(x) for x in np.array(instructions)[:,1]]
    y_values = [float(x) for y in np.array(instructions)[:,2]]

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

def make_crosshatch_image(scalefactor, imarray):
    # Array to be returned
    instructions = []

    # Scale the values in imarray from 0 to MAXINTENSITY
    max_intensity = 255
    minval = imarray.min()
    maxval = imarray.max()
    intensity_scale = max_intensity/(maxval - minval)
    imarray = intensity_scale*(imarray - minval)

    # The center of the image (in units of 0.1 mm) is the point around which it is rotated
    centerx = imarray.shape[1]*scalefactor/2.0
    centery = imarray.shape[0]*scalefactor/2.0

    # startx, starty are the upper left corner of the image
    startx = center[0] - centerx
    starty = center[1] - centery

    # The number of crosshatch layers to lay down
    n_layers = 6
    angle_interval = np.pi/n_layers

    # Start with one line per image row
    print("Computing ", n_layers, " crosshatch arrays")
    filler_pixel_value = max_intensity + 1

    for layer in range(n_layers):
        angle = layer*angle_interval
        print("angle = ", rint(math.degrees(angle)))
        # Ndimage rotate function rotates in the opposite direction of our coordinate system
        # so the angle for our rotation has the same sign as the angle passed to ndimage.rotate
        c = math.cos(angle)
        s = math.sin(angle)

        # Rotate image into bigger array.  Extra pixels generated get set to FILLER_PIXEL_VAL
        rot_array = ndimage.rotate(imarray, math.degrees(angle), mode='constant', cval=filler_pixel_value)
        threshold = max_intensity*(n_layers - layer - 0.25)/n_layers

        # Lower intensity pixels get drawn darker (more lines).  Create an array of booleans
        # which are true if they are part of the line and false if not
        line_array = rot_array < threshold

        # Center of the rotation - we'll need to rotate the line coordinates back around this point
        center_pixel = [line_array.shape[1]/2.0, line_array.shape[0]/2.0]

        direction = 1
        line_start = (0.0, 0.0)
        line_end = (0.0, 0.0)
        ins = []
        for j, row in enumerate(line_array):
            line_started = False
            # Alternate directions in which we traverse the rows
            for i, pixel in (enumerate(row) if (direction > 0) else reversed(list(enumerate(row)))):
                if pixel and not line_started:
                    line_started = True
                    x = scalefactor*(i - center_pixel[0])
                    y = scalefactor*(j - center_pixel[1])
                    if (direction < 0):
                        x = x + scalefactor
                    xp = c*x - s*y
                    yp = s*x + c*y
                    line_start = (center[0] + xp, center[1] + yp)

                elif line_started and not pixel:
                    line_started = False
                    x = scalefactor*(i - center_pixel[0])
                    y = scalefactor*(j - center_pixel[1])
                    if (direction < 0):
                        x = x + scalefactor
                    xp = c*x - s*y
                    yp = s*x + c*y
                    line_end = (center[0] + xp, center[1] + yp)
                    # If line is longer than 1 cm (100 x 0.1 mm), then subdivide it
                    d = distance(line_start, line_end)
                    nseg = max(round_it(d/100), 1)
                    ins = draw_divided_line(line_start, line_end, nseg)
##                    check_out_of_bounds_list(ins)
                    instructions = instructions + ins

            # At the end of each row, finish any lines which have been started
            if line_started:
                line_started = False
                x = direction*scalefactor*center_pixel[0]
                y = scalefactor*(j - center_pixel[1])
                xp = c*x - s*y
                yp = s*x + c*y
                line_end = (center[0] + xp, center[1] + yp)
                d = distance(line_start, line_end)
                nseg = max(round_it(d/100), 1)
                ins = draw_divided_line(line_start, line_end, nseg)
##                check_out_of_bounds_list(ins)
                instructions = instructions + ins

            direction = direction*-1

    # Lift the pen up and get it out of the way after drawing
    instructions.append(['M', rint(origin[0]), round_it(origin[1])])
    return instructions

def make_shaded_image(scalefactor, imarray):

    # Maximum intensity of image pixel
    max_intensity = math.ceil(imarray.max())

    image_size = imarray.shape
    image_width = image_size[1]
    image_height = image_size[0]

    startx = center[0] - image_width * scalefactor /2
    starty = center[1] - image_height *scalefactor /2
    lastx = startx
    lasty = starty

    # First instruction sends pen to starting point
    instructions = [['M', round_it(startx), round_it(starty)]]

    # Maximum number of strokes per pixel.  Calculted to make stroke size a minumum of around 1 mm
    max_strokes = int(size[0]/(max_size*10))


    jitterheight = 2 * scalefactor / 3           #Height of pen strokes
    direction = 1
    # Step through rows of the image
    for i, row in enumerate(imarray):
        # Step through pixels in the row
        for j, pixel in (enumerate(row) if (direction > 0) else reversed(list(enumerate(row)))):
            # Invert image intensity (white=low/dark=high)
            intensity = (max_intensity - pixel)/max_intensity
            jitter = round_it(max_strokes*intensity)

            if jitter == 0:
                lastx = lastx + direction*scalefactor
                instructions.append(['L', round_it(lastx), round_it(lasty)])
            else:
                jitterwidth = scalefactor / jitter

                dx = jitterwidth / 2
                for k in range (0, jitter):
                    instructions.append(['L', round_it(lastx), round_it(lasty + jitterheight)])
                    instructions.append(['L', round_it(lastx + direction*dx), round_it(lasty + jitterheight)])
                    instructions.append(['L', round_it(lastx + direction*dx), round_it(lasty)])
                    instructions.append(['L', round_it(lastx + direction*2*dx), round_it(lasty)])

                    lastx = lastx + direction*jitterwidth
                    # Next pixel

        lasty = starty + (i+1)*scalefactor
        direction = -1*direction
        #Lift the pen carriage up to get to the new line
        instructions.append(['M', round_it(lastx), round_it(lasty)])

    # Get the pen carriage up and out of the way when done
    instructions.append(['M', origin[0], origin[1]])

    #print(instructions[0:50])
    return instructions

# Create instructions list from image
def scalarimage(imfile, shadetype):

    # Import and manipulate the picture
    im = Image.open(imfile)

    # See if aspect ratio of image is greater or less than canvas aspect ratio.
    # Then scalefactor up the image to MAXIMSIZE pixels on the largest side.
    # Add a slight margin for error to make sure we don't exceed boundaries
    scalefactor = 1

    margin = 200
    if im.size[1]/im.size[0] > size[1]/size[0]:

        scalefactor = (size[1] - margin)/max_size
    else:
        scalefactor = (size[0] - margin)/max_size

    im.thumbnail((max_size, max_size), Image.ANTIALIAS)

    # Get new size
    image_size = im.size
    print("imsize = ", image_size)
    print("scalefactor = ", scalefactor)

    #If the image has an alpha channel set all transparent pixels to white
    im = transparent_to_white(im)

    # Show the image on the screen
    showimg(im)

    # Convert image to array
    imarray = np.array(im.convert('L'))


    instructions = []
    if (shadetype == shaded_scalar_image):
        instructions = make_shaded_image(scalefactor, imarray)
    elif (shadetype == crosshatch_scalar_image):
        instructions = make_crosshatch_image(scalefactor, imarray)

    return instructions

def distance(a, b):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)


def draw_divided_line(firstpt, lastpt, n):
    """ Create instructions to draw a line composed of n increments from start to end """

    if (n <= 0):
        print("Can't divide line into 0/- segments")
        return []

    instructions = [['M', round_it(firstpt[0]), round_it(firstpt[1])]]

    xinc = (lastpt[0] - firstpt[0])/n
    yinc = (lastpt[1] - firstpt[1])/n

    for i in range(1, n+1):
        instructions.append(['L', round_it(firstpt[0] + i*xinc), round_it(firstpt[1] + i*yinc)])

    return instructions

def check_out_of_bounds(ins):
    if ((ins[1] < canvasorigin[0]) or
        (ins[1] > canvasorigin[0] + canvassize[0]) or
        (ins[2] < canvasorigin[1]) or
        (ins[2] > canvasorigin[1] + canvassize[1])):
        return True
    else:
        return False


# Checks a list of instructions to see if any of the coordinates are out of bounds
def check_out_of_bounds_list(instructions):
    all_in_bounds = True
    for ins in instructions:
        if check_out_of_bounds(ins):
            print("Out of bounds:", ins)
            all_in_bounds = False

    return all_in_bounds


def draw_test_pattern():
    instructions = []
    """ # Draw a pattern to test the printer """
    margin = 100
    co = [origin[0] + margin, origin[1] + margin]
    cs = [size[0] - margin, size[1] - margin]

    # Draw a square around the perimeter of the canvas
    instructions.append(['M', round_it(co[0]), round_it(co[1])])
    instructions.append(['L', round_it(co[0] + cs[0]), round_it(co[1])])
    instructions.append(['L', round_it(co[0] + cs[0]), round_it(co[1] + cs[1])])
    instructions.append(['L', round_it(co[0]), round_it(co[1] + cs[1])])
    instructions.append(['L', round_it(co[0]), round_it(co[1])])

    # Draw a big 'X' across the square, then return to origin
    instructions.append(['L', round_it(co[0] + cs[0]), round_it(co[1] + cs[1])])
    instructions.append(['M', round_it(co[0] + cs[0]), round_it(co[1])])
    instructions.append(['L', round_it(co[0]), round_it(co[1] + cs[1])])

    # Now draw the same lines broken into smaller steps.  Should be straighter when drawn in segments
    ninc = 40
    instructions = instructions + draw_divided_line([co[0], co[1]], [co[0] + cs[0], co[1]], ninc)
    instructions = instructions + draw_divided_line([co[0] + cs[0], co[1]], [co[0] + cs[0], co[1] + cs[1]], ninc)
    instructions = instructions + draw_divided_line([co[0] + cs[0], co[1] + cs[1]], [cs[1], co[1] + cs[1]], ninc)
    instructions = instructions + draw_divided_line([co[0], co[1] + cs[1]], [co[0], co[1]], ninc)
    instructions = instructions + draw_divided_line([co[0], co[1]], [co[0] + cs[0], co[1] + cs[1]], ninc)
    instructions = instructions + draw_divided_line([co[0] + cs[0], co[1]], [co[0], co[1] + cs[1]], ninc)
    instructions.append(['M', round_it(co[0]), round_it(co[1])])

    #check_out_of_bounds(instructions)
    return instructions

def main():

    # Show askopenfilename dialog without the Tkinter window
    root = tkinter.Tk()
    root.withdraw()
    dirname = ""
    if (current_os == os_windows):
        dirname = "C:\Users\wyckl\Documents\crispy-enigma\img\"
    elif (current_os == os_raspbian):
        dirname = "/home/pi/WallPlotterImages"
    filename = filedialog.askopenfilename(title="Chose a Data File",
                                          initialdir=dirname,
                                          filetypes=[('all files', '.*'), ('jpg files', '.jpg')])
    print(filename)

    print("Enter graphics type:")
    print("(1) Image file shading")
    print("(2) Image file crosshatch")
    print("(3) GCode")
    print("(4) Test Pattern")
    option = int(input("Select number of desired option "))

    instructions = []
    if option == 1:
        instructions = scalarimage(filename, shaded_scalar_image)
    elif option == 2:
        instructions = scalarimage(filename, crosshatch_scalar_image)
    elif option == 3:
        instructions = vectorimage(filename)
    elif option == 4:
        instructions = draw_test_pattern()

    # Open serial connection to Arduino -> TBD set correct port
    port_name = ""
    if (current_os == os_windows):
        port_name = "COM34"
    elif(current_os == os_raspbian):
        port_name = "/dev/ttyUSB0"
    arduino = serial.Serial(port=port_name, baudrate=57600)
    print(arduino.name)

    # Wait for connection to establish
    connected = False
    while not connected:
        serin = arduino.read()
        connected = True

    # Send directions to the Arduino and listen for feedback
    while True:
        line = arduino.readline()
        if line:
            cmd = processdata(line)
            if (cmd == cmd_console):
                print(line)
            elif (cmd == cmd_ok):
                if len(instructions) == 0:
                    print("finished")
                else:
                    # Obtain and remove the first instruction from the list
                    inst = instructions.pop(0)
                    buf = "%c %d %d;" % (inst[0], inst[1], inst[2])
                    #print("buf = " + buf)
                    arduino.write(buf.encode('ascii'))
            else:
                print("Command received but not understood:")
                print(line)


main()
