import time
from PIL import Image
import random, math
from math import sin, cos, pi, sqrt


# Your job is to create better version of create_expression and
# run_expression to create random art.
# Your expression should have a __str__() function defined for it.


###Pure maths
class X:
   def eval(self, x, y):
      return x
   
   def __str__(self):
      return "x"

class Y:
   def eval(self, x, y):
      return y
   
   def __str__(self):
      return "y"

class SinPi:
   def __init__(self, prob):
      self.arg = buildExpr(prob * prob)
   
   def __str__(self):
      return "sin(pi*" + str(self.arg) + ")"

   def eval(self, x, y):
      return math.sin(math.pi * self.arg.eval(x,y))

class CosPi:
   def __init__(self, prob):
      self.arg = buildExpr(prob * prob)

   def __str__(self):
      return "cos(pi*" + str(self.arg) + ")"

   def eval(self, x, y):
      return math.cos(math.pi * self.arg.eval(x,y))

class Times:
   def __init__(self, prob):
      self.lhs = buildExpr(prob * prob)
      self.rhs = buildExpr(prob * prob)

   def __str__(self):
      return str(self.lhs) + "*" + str(self.rhs)

   def eval(self, x, y):
      return self.lhs.eval(x,y) * self.rhs.eval(x,y)

def buildExpr(prob = 0.99):
   if random.random() < prob:
      return random.choice([SinPi, CosPi, Times])(prob)
   else:
      return random.choice([X, Y])()

def plotIntensity(exp, pixelsPerUnit = 150):
    canvasWidth = 2 * pixelsPerUnit + 1
    canvas = Image.new("L", (canvasWidth, canvasWidth))

    for py in range(canvasWidth):
        for px in range(canvasWidth):
            # Convert pixel location to [-1,1] coordinates
            x = float(px - pixelsPerUnit) / pixelsPerUnit 
            y = -float(py - pixelsPerUnit) / pixelsPerUnit
            z = exp.eval(x,y)

            # Scale [-1,1] result to [0,255].
            intensity = int(z * 127.5 + 127.5)
            canvas.putpixel((px,py), intensity)

    return canvas

def plotColor(redExp, greenExp, blueExp, pixelsPerUnit = 3):
    redPlane   = plotIntensity(redExp, pixelsPerUnit)
    greenPlane = plotIntensity(greenExp, pixelsPerUnit)
    bluePlane  = plotIntensity(blueExp, pixelsPerUnit)
    return Image.merge("RGB", (redPlane, greenPlane, bluePlane))


###Pure maths
def geometric_mean(*args):
    multiplicative_sum = 1
    for arg in args:
        multiplicative_sum *= (abs(arg) +1)
    return pow(multiplicative_sum, -len(args))


def avg(*args):
    return sum(args) / len(args)


def create_expression():
    """This function takes no arguments and returns an expression that
    generates a number between -1.0 and 1.0, given x and y coordinates."""
    function_list = []
    function_list.append(lambda x, y: sin(pi * (sin(y /2) * 2) - 1 + cos(x) * geometric_mean(x, y)))
    function_list.append(lambda x, y: sin(x * sin(y)) + avg(0.5, x))
    expr = random.choice(function_list)
    return expr


def run_expression(expr, x, y):
    """This function takes an expression created by create_expression and
    an x and y value. It runs the expression, passing the x and y values
    to it and returns a value between -1.0 and 1.0."""

    return expr(x, y)


def generate_monochrome_image(expression, width=384, height=216):
    """Return a grayscale image of the given expression."""
    
    zx = random.randint(1, 31)
    zy = random.randint(1, 31)
    def convert_coords(x, y):
        """Convert absolute coordinates to relative coords
        between (-1, -1) and (1, 1)."""
        width_unit = width / zx
        height_unit = height / zy
        rx = (x - width_unit) / width_unit
        ry = (y - height_unit) / height_unit
        return (rx, ry)

    def scale_intensity(rel_intensity):
        """Convert a relative intensity from [-1, 1] to [0,255]."""
        return int(rel_intensity * 127.5 + 127.5)

    image = Image.new("L", (width, height))

    # Go through each pixel in the image.
    # We will convert each coordinate to a coordinate between
    # (-1, -1) and (1, 1) before passing it to our expression.
    for py in range(height):
        for px in range(width):
            x, y = convert_coords(px, py)
            expr_value = run_expression(expression, x, y)
            intensity = scale_intensity(expr_value)
            image.putpixel((px, py), intensity)

    return image


def generate_rgb_image(red_exp, green_exp, blue_exp, width=34, height=34):
    red_image = generate_monochrome_image(red_exp, width)
    green_image = generate_monochrome_image(green_exp, width)
    blue_image = generate_monochrome_image(blue_exp, width)
    return Image.merge("RGB", (red_image, green_image, blue_image))