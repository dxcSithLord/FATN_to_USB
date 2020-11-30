#!/usr/bin/python3

import argparse
from scrolling_text import do_mes

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
try:
  import ST7789 as ST7789
  disp = ST7789.ST7789(
    port=0,
    cs=ST7789.BG_SPI_CS_FRONT,  # BG_SPI_CSB_BACK or BG_SPI_CS_FRONT
    dc=9,
    backlight=19,               # 18 for back BG slot, 19 for front BG slot.
    spi_speed_hz=80 * 1000 * 1000
  )
except BaseException as exception:
  print('ST7789 not available %s'%repr(exception))

try:
  import ST7735 as ST7735
  disp = ST7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
  )
except BaseException as exception:
  print('ST7735 not available %s'%repr(exception))


do_mes(disp,mess,colour)

