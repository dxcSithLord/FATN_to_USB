import os
import logging

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import time

# Import display detection module
from fatn_to_usb import display_detector

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Initialize display using detection system
_display_info = display_detector.get_display_info()
disp = _display_info.display_instance

# Print detection summary
print('\n' + '=' * 60)
print('Display Configuration Summary:')
print(f'  Display Type: {_display_info.display_type or "None"}')
print(f'  Raspberry Pi: {_display_info.pi_model}')
if _display_info.is_zero:
    print(f'  Pi Zero 2: {_display_info.is_zero_2}')
print(f'  GUI: {_display_info.gui_type or "None (console-only)"}')
print('=' * 60 + '\n')

def do_mes(display, MESSAGE='', colour=(0,255,0)):
    ''' procedure to put message with background colour onto display '''
    # MESSAGE = "USB     FATN    READY     LOAD"

    # Handle case where no display is available
    if display is None:
        # Fallback to console output
        print(f'\n[DISPLAY] {MESSAGE}')
        if _display_info.display_type == 'console':
            print('Output method: Console-only (Debian Trixie Slim)')
        elif _display_info.display_type == 'framebuffer':
            print('Output method: Framebuffer (/dev/fb0 available)')
        else:
            print('Output method: Logging only (no display hardware)')
        return

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
