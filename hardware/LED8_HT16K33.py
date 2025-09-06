#####
#    A simple, generic driver for the I2C-connected HT16K33 controller chip.
#    Language:                        Micropython
#    Bus:                             I2C
#    Based on code originally by:     Tony Smith (@smittytone)
#    License:                         MIT
#    Copyright:                       2025
#####

class HT16K33:

    # *********** CONSTANTS **********

    HT16K33_GENERIC_DISPLAY_ON = 0x81
    HT16K33_GENERIC_DISPLAY_OFF = 0x80
    HT16K33_GENERIC_SYSTEM_ON = 0x21
    HT16K33_GENERIC_SYSTEM_OFF = 0x20
    HT16K33_GENERIC_DISPLAY_ADDRESS = 0x00
    HT16K33_GENERIC_CMD_BRIGHTNESS = 0xE0
    HT16K33_GENERIC_CMD_BLINK = 0x81

    # *********** PRIVATE PROPERTIES **********

    i2c = None
    address = 0
    brightness = 15
    flash_rate = 0

    # *********** CONSTRUCTOR **********

    def __init__(self, i2c, i2c_address):
        assert 0x00 <= i2c_address < 0x80, "ERROR - Invalid I2C address in HT16K33()"
        self.i2c = i2c
        self.address = i2c_address
        self.power_on()

    # *********** PUBLIC METHODS **********

    def set_blink_rate(self, rate=0):
        """
        Set the display's flash rate.

        Only four values (in Hz) are permitted: 0, 2, 1, and 0.5.

        Args:
            rate (int): The chosen flash rate. Default: 0Hz (no flash).
        """
        allowed_rates = (0, 2, 1, 0.5)
        assert rate in allowed_rates, "ERROR - Invalid blink rate set in set_blink_rate()"
        self.blink_rate = allowed_rates.index(rate) & 0x03
        self._write_cmd(self.HT16K33_GENERIC_CMD_BLINK | self.blink_rate << 1)

    def set_brightness(self, brightness=15):
        """
        Set the display's brightness (ie. duty cycle).

        Brightness values range from 0 (dim, but not off) to 15 (max. brightness).

        Args:
            brightness (int): The chosen flash rate. Default: 15 (100%).
        """
        if brightness < 0 or brightness > 15: brightness = 15
        self.brightness = brightness
        self._write_cmd(self.HT16K33_GENERIC_CMD_BRIGHTNESS | brightness)

    def draw(self):
        """
        Writes the current display buffer to the display itself.

        Call this method after updating the buffer to update
        the LED itself.
        """
        self._render()

    def update(self):
        """
        Alternative for draw() for backwards compatibility
        """
        self._render()

    def clear(self):
        """
        Clear the buffer.

        Returns:
            The instance (self)
        """
        for i in range(0, len(self.buffer)): self.buffer[i] = 0x00
        return self

    def power_on(self):
        """
        Power on the controller and display.
        """
        self._write_cmd(self.HT16K33_GENERIC_SYSTEM_ON)
        self._write_cmd(self.HT16K33_GENERIC_DISPLAY_ON)

    def power_off(self):
        """
        Power on the controller and display.
        """
        self._write_cmd(self.HT16K33_GENERIC_DISPLAY_OFF)
        self._write_cmd(self.HT16K33_GENERIC_SYSTEM_OFF)

    # ********** PRIVATE METHODS **********

    def _render(self):
        """
        Write the display buffer out to I2C
        """
        buffer = bytearray(len(self.buffer) + 1)
        buffer[1:] = self.buffer
        buffer[0] = 0x00
        self.i2c.writeto(self.address, bytes(buffer))

    def _write_cmd(self, byte):
        """
        Writes a single command to the HT16K33. A private method.
        """
        self.i2c.writeto(self.address, bytes([byte]))


"""
    Micropython class for a generic 1-8-digit, 7-segment display.
    It assumes each digit has a decimal point, but there are no other
    symbol LEDs included.

    Bus:        I2C
    Author:     Tony Smith (@smittytone)
    License:    MIT
    Copyright:  2025
"""

class HT16K33LED(HT16K33):

    # *********** CONSTANTS **********

    HT16K33_SEGMENT_MINUS_CHAR = 0x40
    HT16K33_SEGMENT_DEGREE_CHAR = 0x63
    HT16K33_SEGMENT_SPACE_CHAR = 0x00

    CHARSET = {
        '0': 0x3F,
        '1': 0x06,
        '2': 0x5B,
        '3': 0x4F,
        '4': 0x66,
        '5': 0x6D,
        '6': 0x7D,
        '7': 0x07,
        '8': 0x7F,
        '9': 0x6F,
        'a': 0x77,
        'b': 0x7C,
        'c': 0x39,
        'd': 0x5E,
        'e': 0x79,
        'f': 0x71,
        'g': 0x3D,
        'h': 0x76,
        'i': 0x06,
        'j': 0x1E,
        'k': 0x75,
        'l': 0x38,
        'm': 0x37,
        'n': 0x54,
        'o': 0x5C,
        'p': 0x73,
        'q': 0x67,
        'r': 0x50,
        's': 0x6D,
        't': 0x78,
        'u': 0x3E,
        'v': 0x1C,
        'w': 0x2A,
        'x': 0x76,
        'y': 0x6E,
        'z': 0x5B,
        ' ': 0x00,
        '-': 0x40,
        '°': 0x63,
        '=': 0x48,
        '_': 0x08,
        '*': 0x63,
        '.': 0x80
    }

    # *********** CONSTRUCTOR **********

    def __init__(self, i2c, i2c_address=0x70, digits=8):
        self.buffer = bytearray(16)
        self.is_rotated = False
        # Check digits specified (must be 1 - 8)
        assert 0 < digits < 9, "ERROR - Invalid number of digits (1-8) in HT16K33Segment8()"
        self.max_digits = digits
        super(HT16K33LED, self).__init__(i2c, i2c_address)

    # *********** PUBLIC METHODS **********

    def rotate(self):
        """
        Rotate/flip the segment display.

        Returns:
            The instance (self)
        """
        self.is_rotated = not self.is_rotated
        return self

    def set_glyph(self, glyph, digit=0, has_dot=False):
        """
        Present a user-defined character glyph at the specified digit.

        Glyph values are 8-bit integers representing a pattern of set LED segments.
        The value is calculated by setting the bit(s) representing the segment(s) you want illuminated.
        Bit-to-segment mapping runs clockwise from the top around the outside of the matrix; the inner segment is bit 6:

                0
                _
            5 |   | 1
              |   |
                - <----- 6
            4 |   | 2
              | _ |
                3

        This method updates the display buffer, but does not send the buffer to the display itself.
        Call 'update()' to render the buffer on the display.

        Args:
            glyph (int):   The glyph pattern.
            digit (int):   The digit to show the glyph. Default: 0 (leftmost digit).
            has_dot (bool): Whether the decimal point to the right of the digit should be lit. Default: False.

        Returns:
            The instance (self)
        """
        # Bail on incorrect row numbers or character values
        assert 0 <= digit < self.max_digits, "ERROR - Invalid digit set in set_glyph()"
        assert 0 <= glyph < 0x80, "ERROR - Invalid glyph (0x00-0x80) set in set_glyph()"

        self.buffer[digit << 1] = glyph
        if has_dot is True: self.buffer[digit << 1] |= 0x80
        return self

    def set_number(self, number, digit=0, has_dot=False):
        """
        Present single decimal value (0-9) at the specified digit.

        This method updates the display buffer, but does not send the buffer to the display itself.
        Call 'update()' to render the buffer on the display.

        Args:
            number (int):  The number to show.
            digit (int):   The digit to show the number. Default: 0 (leftmost digit).
            has_dot (bool): Whether the decimal point to the right of the digit should be lit. Default: False.

        Returns:
            The instance (self)
        """
        # Bail on incorrect row numbers or character values
        assert 0 <= digit < self.max_digits, "ERROR - Invalid digit set in set_number()"
        assert 0 <= number < 10, "ERROR - Invalid value (0-9) set in set_number()"

        return self.set_character(str(number), digit, has_dot)

    def set_string(self, string, alignment):
        """
        Write a string of up to 8 digits to the buffer, by alignment
        
        """
        expanded = []
        i = 0

        while i < len(string) and len(expanded) < 8:
            char = string[i]
            has_dot = False

            if char == "." and expanded and expanded[-1][0] == " ":
                # Special case: dot immediately after a space = empty digit with dot
                expanded.append((" ", True))
                i += 1
                continue

            # If next char is '.', attach it as decimal point
            if i + 1 < len(string) and string[i + 1] == ".":
                has_dot = True
                i += 1  # skip the dot
            
            expanded.append((char, has_dot))
            i += 1

        str_length = len(expanded)
        pad_length = 8 - str_length

        if alignment == "r":
            expanded = [(" ", False)] * pad_length + expanded
        else:
            expanded = expanded + [(" ", False)] * pad_length

        # Now send characters to buffer
        for k in range(8):
            char, has_dot = expanded[k]
            self.set_character(char, k, has_dot)
        
        return self.draw()


    def set_character(self, char, digit=0, has_dot=False):
        """
        Present single alphanumeric character at the specified digit.

        Only characters from the class' character set are available:
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, a, b, c, d ,e, f, -.
        Other characters can be defined and presented using 'set_glyph()'.

        This method updates the display buffer, but does not send the buffer to the display itself.
        Call 'update()' to render the buffer on the display.

        Args:
            char (string):  The character to show.
            digit (int):    The digit to show the number. Default: 0 (leftmost digit).
            has_dot (bool): Whether the decimal point to the right of the digit should be lit. Default: False.

        Returns:
            The instance (self)
        """
        # Bail on incorrect row numbers
        assert 0 <= digit < self.max_digits, "ERROR - Invalid digit set in set_character()"

        char = char.lower()
        char_val = self.CHARSET.get(char, None)
        assert char_val is not None, f"ERROR - Invalid char '{char}' in set_character()"
        
        self.buffer[digit << 1] = char_val
        if has_dot:
            self.buffer[digit << 1] |= 0x80
        return self

    def draw(self):
        """
        Writes the current display buffer to the display itself.

        Call this method after updating the buffer to update
        the LED itself. Rotation handled here.
        """
        if self.is_rotated:
            # Preserve the unrotated buffer
            tmpbuffer = bytearray(16)
            for i in range(0, self.max_digits << 1):
                tmpbuffer[i] = self.buffer[i]
            # Swap digits 0,(max - 1), 1,(max - 2) etc
            if self.max_digits > 1:
                for i in range(0, (self.max_digits >> 1)):
                    right = (self.max_digits - i - 1) << 1
                    left = i << 1
                    if left != right:
                        a = self.buffer[left]
                        self.buffer[left] = self.buffer[right]
                        self.buffer[right] = a

            # Flip each digit
            for i in range(0, self.max_digits):
                a = self.buffer[i << 1]
                b = (a & 0x07) << 3
                c = (a & 0x38) >> 3
                a &= 0xC0
                self.buffer[i << 1] = (a | b | c)
            self._render()
            # Restore the buffer
            for i in range(0, self.max_digits << 1):
                self.buffer[i] = tmpbuffer[i]
        else:
            self._render()
