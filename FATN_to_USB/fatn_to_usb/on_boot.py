#!/usr/bin/python3
"""
On-boot script for displaying messages using the display detection system.

Usage:
  python on_boot.py -m "Hello World" -r 255 -g 0 -b 0
"""

import argparse
from scrolling_text import do_mes, disp

# Construct the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-m", "--message", default='', required = False,
        help = "Enter message and colour")
ap.add_argument( "-r", "--red", default=0, required = False, type =int,
        help = "Enter colour in (RGB) values")
ap.add_argument( "-g", "--green", default=255, required = False,
        type= int,
        help = "Enter colour in (RGB) values")
ap.add_argument( "-b", "--blue", default=0, required = False, type= int,
        help = "Enter colour in (RGB) values")
args = vars(ap.parse_args())
mess= args["message"]
colour = (args["red"],args["green"],args["blue"])
print('colour = %s' % str(colour))

# Display is already initialized by scrolling_text module
# which uses the display_detector system
do_mes(disp, mess, colour)

