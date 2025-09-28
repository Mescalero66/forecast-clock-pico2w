# MicroPython SSD1306 OLED driver, I2C and SPI interfaces
#
# library taken from repository at:
# https://github.com/micropython/micropython/blob/master/drivers/display/ssd1306.py

from micropython import const
from struct import pack_into
import framebuf

# register definitions
SET_CONTRAST = const(0x81)
SET_ENTIRE_ON = const(0xA4)
SET_NORM_INV = const(0xA6)
SET_DISP = const(0xAE)
SET_MEM_ADDR = const(0x20)
SET_COL_ADDR = const(0x21)
SET_PAGE_ADDR = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xA0)
SET_MUX_RATIO = const(0xA8)
SET_COM_OUT_DIR = const(0xC0)
SET_DISP_OFFSET = const(0xD3)
SET_COM_PIN_CFG = const(0xDA)
SET_DISP_CLK_DIV = const(0xD5)
SET_PRECHARGE = const(0xD9)
SET_VCOM_DESEL = const(0xDB)
SET_CHARGE_PUMP = const(0x8D)

# constants
BANNER_HEIGHT = 16
PAGE_HEIGHT = 48

# Subclassing FrameBuffer provides support for graphics primitives
# http://docs.micropython.org/en/latest/pyboard/library/framebuf.html

class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.load_font()
        self.init_display()

    def init_display(self):
        for cmd in (
            SET_DISP | 0x00,  # off
            # address setting
            SET_MEM_ADDR,
            0x00,  # horizontal
            # resolution and layout
            SET_DISP_START_LINE | 0x00,
            SET_SEG_REMAP | 0x01,  # column addr 127 mapped to SEG0
            SET_MUX_RATIO,
            self.height - 1,
            SET_COM_OUT_DIR | 0x08,  # scan from COM[N] to COM0
            SET_DISP_OFFSET,
            0x00,
            SET_COM_PIN_CFG,
            0x02 if self.width > 2 * self.height else 0x12,
            # timing and driving scheme
            SET_DISP_CLK_DIV,
            0x80,
            SET_PRECHARGE,
            0x22 if self.external_vcc else 0xF1,
            SET_VCOM_DESEL,
            0x30,  # 0.83*Vcc
            # display
            SET_CONTRAST,
            0xFF,  # maximum
            SET_ENTIRE_ON,  # output follows RAM contents
            SET_NORM_INV,  # not inverted
            # charge pump
            SET_CHARGE_PUMP,
            0x10 if self.external_vcc else 0x14,
            SET_DISP | 0x01,
        ):  # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def _set_pos(self, col=0, page=0):
            self.write_cmd(0xb0 | page)  # page number
            # take upper and lower value of col * 2
            c1, c2 = col * 2 & 0x0F, col >> 3
            self.write_cmd(0x00 | c1)  # lower start column address
            self.write_cmd(0x10 | c2)  # upper start column address

    def poweroff(self):
        self.write_cmd(SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            page, shift_page = divmod(y, 8)
            ind = x + page * self.width
            if color:
                self.buffer[ind] |= (1 << shift_page)
            else:
                self.buffer[ind] &= ~(1 << shift_page)
            
            # x = x & (self.width - 1)
            # y = y & (self.height - 1)
            # page, shift_page = divmod(y, 8)
            # ind = x + page * 128
            # b = self.buffer[ind] | (1 << shift_page) if color else self.buffer[ind] & ~ (1 << shift_page)
            # pack_into(">B", self.buffer, ind, b)
            # self._set_pos(x, page)
    
    def circ(self,x,y,r,t=1,c=1):
        r2 = r * r
        if t > 1:
            rmin2 = (r - r*t - 1) ** 2
        for i in range(x-r, x+r+1):
            dx2 = (i-x) * (i-x)
            for j in range(y-r, y+r+1):
                dy2 = (j-y) * (j-y)
                d2 = dx2 + dy2
                if t == 1:
                    if d2 < r2:
                        self.pixel(i, j, c)
                else:
                    if rmin2 <= d2 < r2:
                       self.pixel(i, j, c)
    
    def line(self, x1, y1, x2, y2, c):
            # bresenham
            steep = abs(y2-y1) > abs(x2-x1)
            
            if steep:
                # Swap x/y
                tmp = x1
                x1 = y1
                y1 = tmp
                
                tmp = y2
                y2 = x2
                x2 = tmp
            
            if x1 > x2:
                # Swap start/end
                tmp = x1
                x1 = x2
                x2 = tmp
                tmp = y1
                y1 = y2
                y2 = tmp
            
            dx = x2 - x1;
            dy = abs(y2-y1)
            
            err = dx/2
            
            if(y1 < y2):
                ystep = 1
            else:
                ystep = -1
                
            while x1 <= x2:
                if steep:
                    self.pixel(y1, x1, c)
                else:
                    self.pixel(x1, y1, c)
                err -= dy
                if err < 0:
                    y1 += ystep
                    err += dx
                x1 += 1        
    
    def hline(self, x, y, l, c):
        self.line(x, y, x + l, y, c)
            
    def vline(self, x, y, h, c):
        self.line(x, y, x, y + h, c)
            
    def rect(self, x, y, w, h, c):
        self.hline(x, y, w, c)
        self.hline(x, y+h, w, c)
        self.vline(x, y, h, c)
        self.vline(x+w, y, h, c)
                    
    def fill(self, c):
        for i in range(0, self.height):
            self.hline(0, i, self.width, c)
    
    def fill_rect(self, x, y, w, h, c):
        for i in range(y, y + h):
            self.hline(x, i, w, c)
        
    def load_font(self, filename="font-pet-me-128.dat"):
        with open(filename, "rb") as f:
            self.font = bytearray(f.read())

    def text(self, text, x, y, c=1):
        text = str(text)
        for text_index in range(len(text)):
            for col in range(8):
                fontDataPixelValues = self.font[(ord(text[text_index]) - 32) * 8 + col]
                for i in range(7):
                    if fontDataPixelValues & 1 << i != 0:
                        x_coordinate = x + col + text_index * 8
                        y_coordinate = y + i
                        if x_coordinate < self.width and y_coordinate < self.height:
                            self.pixel(x_coordinate, y_coordinate, c)
    
    def year_text(self, text):
        text = str(text)
        x = 48
        y = 56
        c = 1
        for text_index in range(len(text)):
            for col in range(8):
                fontDataPixelValues = self.font[(ord(text[text_index]) - 32) * 8 + col]
                for i in range(7):
                    if fontDataPixelValues & 1 << i != 0:
                        x_coordinate = x + col + text_index * 8
                        y_coordinate = y + i
                        if x_coordinate < self.width and y_coordinate < self.height:
                            self.pixel(x_coordinate, y_coordinate, c)

    def text_inverted(self, text, x, y, c=1):
        text = str(text)
        for text_index in range(len(text)):
            for col in range(8):
                fontDataPixelValues = self.font[(ord(text[text_index]) - 32) * 8 + col]
                for i in range(7):
                    pixel_on = (fontDataPixelValues & (1 << i)) != 0
                    x_coordinate = x + col + text_index * 8
                    y_coordinate = y + i
                    if 0 <= x_coordinate < self.width and 0 <= y_coordinate < self.height:
                        self.pixel(x_coordinate, y_coordinate, 0 if pixel_on else c)
    
    def banner_text(self, text, c=1):
        text = str(text)
        total_width = len(text) * 14  # 14 pixels per char horizontally
        x_start = (self.width - total_width) // 2  # center
        y = 1

        for text_index in range(len(text)):
            for col in range(8):
                fontDataPixelValues = self.font[(ord(text[text_index]) - 32) * 8 + col]
                for i in range(8):
                    if fontDataPixelValues & 1 << i != 0:
                        x_coord = x_start + (col * 2) + (text_index * 14)
                        y_coordinate = y + (i * 2)
                        if x_coord < self.width and y_coordinate < self.height:
                            for iY in range(2):
                                self.pixel(x_coord, y_coordinate - iY, c)
                                self.pixel(x_coord - 1, y_coordinate - iY, c)
    
    def banner_text_inverted(self, text, c=0):
        text = str(text)
        total_width = len(text) * 14  # 14 pixels per char horizontally
        x_start = (self.width - total_width) // 2  # center
        y = 2

        self.fill_rect(0,0,self.width,BANNER_HEIGHT,1)

        for text_index in range(len(text)):
            for col in range(8):
                fontDataPixelValues = self.font[(ord(text[text_index]) - 32) * 8 + col]
                for i in range(8):
                    if fontDataPixelValues & 1 << i != 0:
                        x_coord = x_start + (col * 2) + (text_index * 14)
                        y_coordinate = y + (i * 2)
                        if x_coord < self.width and y_coordinate < self.height:
                            for iY in range(2):
                                self.pixel(x_coord, y_coordinate - iY, c)
                                self.pixel(x_coord - 1, y_coordinate - iY, c)
                
    def subbanner_text(self, text, x, y, c=1):
        text = str(text)
        total_width = len(text) * 8
        if x is None:
            x = (self.width - total_width) // 2

        if y is None:
            y = (BANNER_HEIGHT)

        for text_index in range(len(text)):
            for col in range(8):
                fontDataPixelValues = self.font[(ord(text[text_index]) - 32) * 8 + col]
                for i in range(7):
                    if fontDataPixelValues & (1 << i) != 0:
                        x_coordinate = x + col + text_index * 8
                        y_coordinate = y + i
                        if x_coordinate < self.width and y_coordinate < self.height:
                            self.pixel(x_coordinate, y_coordinate, c)

    def custom_text(self, text, y=0, font_width = 8, font_height = 8, scale = 1, c=1):
        text = str(text)
        scale_x = scale * 3
        scale_y = scale * 4
        char_width = font_width * scale_x + 2
        char_height = font_height * scale_y

        # Horizontal centering
        total_width = len(text) * char_width
        x_start = (self.width - total_width) // 2

        # Draw each character
        for text_index, char in enumerate(text):
            for col in range(font_width):
                font_byte = self.font[(ord(char) - 32) * font_width + col]
                x_pos = x_start + text_index * char_width + col * scale_x
                for dx in range(scale_x):                                   # horizontal scaling
                    x = x_pos + dx
                    if x >= self.width:
                        continue
                    for row in range(font_height):
                        pixel_on = (font_byte >> row) & 1
                        if pixel_on:
                            y_pos = y + row * scale_y
                            for dy in range(scale_y):                       # vertical scaling
                                y = y_pos + dy
                                if y < self.height:
                                    self.pixel(x, y, c)

    def date_text(self, text, y_start=0, c=1):
        text = str(text)
        font_width = 8                          # font is 8 pixels wide
        font_height = 8                         # font is 8 pixels tall
        scale_x = 3                             # horizontal scaling
        scale_y = 4                             # vertical scaling
        y_offset = 16                           # start under the banner
        char_width = font_width * scale_x + 2   # 8 * 2 + 2 spacing = 18 (approx)
        char_height = font_height * scale_y     # 16 pixels high

        # Horizontal centering
        total_width = len(text) * char_width
        x_start = (self.width - total_width) // 2

        # Vertical centering
        y_start = y_offset + (48 - char_height) // 2

        # Draw each character
        for text_index, char in enumerate(text):
            for col in range(font_width):
                font_byte = self.font[(ord(char) - 32) * font_width + col]
                x_pos = x_start + text_index * char_width + col * scale_x
                for dx in range(scale_x):                                   # horizontal scaling
                    x = x_pos + dx
                    if x >= self.width:
                        continue
                    for row in range(font_height):
                        pixel_on = (font_byte >> row) & 1
                        if pixel_on:
                            y_pos = y_start + row * scale_y
                            for dy in range(scale_y):                       # vertical scaling
                                y = y_pos + dy
                                if y < self.height:
                                    self.pixel(x, y, c)
    
    def show(self):
        # x0 = 0
        # x1 = self.width - 1
        # if self.width == 64:
        #     # displays with width of 64 pixels are shifted by 32
        #     x0 += 32
        #     x1 += 32
        # self.write_cmd(SET_COL_ADDR)
        # self.write_cmd(x0)
        # self.write_cmd(x1)
        # self.write_cmd(SET_PAGE_ADDR)
        # self.write_cmd(0)
        # self.write_cmd(self.pages - 1)
        # self.write_data(self.buffer)

        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            # displays with width of 64 pixels are shifted by 32
            x0 += 32
            x1 += 32

        for page in range(self.pages):
            # set column address range
            self.write_cmd(SET_COL_ADDR)
            self.write_cmd(x0)
            self.write_cmd(x1)

            # set current page
            self.write_cmd(SET_PAGE_ADDR)
            self.write_cmd(page)
            self.write_cmd(page)

            # send one page of buffer (width bytes)
            start = page * self.width
            end = start + self.width
            self.write_data(self.buffer[start:end])


class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.write_list = [b"\x40", None]  # Co=0, D/C#=1
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.i2c.writeto(self.addr, b'\x40' + buf)

class SSD1306_SPI(SSD1306):
    def __init__(self, width, height, spi, dc, res, cs, external_vcc=False):
        self.rate = 10 * 1024 * 1024
        dc.init(dc.OUT, value=0)
        res.init(res.OUT, value=0)
        cs.init(cs.OUT, value=1)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        import time

        self.res(1)
        time.sleep_ms(1)
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)