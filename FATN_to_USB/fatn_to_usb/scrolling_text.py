from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import time

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

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
  print('ST7789 not available %s' % repr(exception))

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
  print('ST7735 not available %s' % repr(exception))

def do_mes(display, MESSAGE='', colour=(0,255,0)):
    ''' procedure to put message with background colour onto display '''
    # MESSAGE = "USB     FATN    READY     LOAD"

    # Initialize display.
    display.begin()

    WIDTH = display.width
    HEIGHT = display.height
    GREEN=(0,128,0)

    img = Image.new('RGB', (WIDTH, HEIGHT), color=GREEN)

    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype( FONT_PATH, 50)

    size_x, size_y = draw.textsize(MESSAGE, font)
    print('size_x %s\nsize_y %s' % (size_x, size_y))

    text_x = (display.width - size_x) // 2
    text_y = (80 - size_y) // 2
    print('text_x %s\ntext_y %s' % (text_x, text_y))


    draw.rectangle((0, 0, display.width, 80), colour)
    if MESSAGE!='':
        if disp.width < size_x:
            t_start = time.time()
            while time.time() < (t_start + 120):
                x = (time.time() - t_start) * 100
                x %= (size_x + disp.width)
                draw.rectangle((0, 0, disp.width, 80), GREEN)
                draw.text((int(text_x - x), text_y), 
                          MESSAGE, font=font, 
                          fill=(255, 255, 255))
                display.display(img)
        else:
            draw.text((text_x, text_y), MESSAGE, font=font, fill=(255, 255, 255))
    display.display(img)

if __name__ =='__main__':
    do_mes(disp, MESSAGE='FRED', colour=(128,128,0))

#while True:
#    x = (time.time() - t_start) * 100
#    x %= (size_x + disp.width)
#    draw.rectangle((0, 0, disp.width, 80), GREEN)
#    draw.text((int(text_x - x), text_y), MESSAGE, font=font, fill=(255, 255, 255))
#    disp.display(img)
