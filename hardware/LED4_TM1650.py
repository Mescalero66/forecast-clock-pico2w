# MIT License
# Copyright (c) 2025 Mescalero
# v0.8 - Released 20250724
# 
# Micropython Driver for:
# DFRobot DFR0645-R DFR0645-G <https://wiki.dfrobot.com/4-Digital%20LED%20Segment%20Display%20Module%20%20SKU:%20DFR0645-G_DFR0645-R>
# NOTE: THIS IS NOT AN I2C DEVICE 
#
# Shout out to CarlWilliamsBristol <https://github.com/CarlWilliamsBristol/pxt-tm1650display>
# TM1650 Datasheet <https://bafnadevices.com/wp-content/uploads/2024/04/TM1650_V2.2_EN.pdf>

from machine import Pin
import time

DEFAULT_PULSE_WIDTH = 120                   # microseconds
DEFAULT_HALF_PULSE_WIDTH = 60
DEFAULT_SYSTEM_COMMAND = 0x48
DEFAULT_READ_COMMAND = 0x49

characterBytes = [
    0x3F,  # 0
    0x06,  # 1
    0x5B,  # 2
    0x4F,  # 3
    0x66,  # 4
    0x6D,  # 5
    0x7D,  # 6
    0x07,  # 7
    0x7F,  # 8
    0x6F,  # 9
    0x77,  # A
    0x7C,  # b
    0x39,  # C
    0x5E,  # d
    0x79,  # E
    0x71,  # F
    0x3D,  # G
    0x76,  # H
    0x06,  # I
    0x1E,  # J
    0x75,  # K (approx: H + diagonal)
    0x38,  # L
    0x37,  # M (approx: N + diagonal)
    0x54,  # N
    0x5C,  # o
    0x73,  # P
    0x67,  # Q
    0x50,  # R
    0x6D,  # S
    0x78,  # T
    0x3E,  # U
    0x1C,  # V
    0x2A,  # W (approx)
    0x76,  # X (use H as approx)
    0x6E,  # Y
    0x5B,  # Z
    0x00,  # [36] space
    0x40,  # [37] dash -
    0x63,  # [38] degrees °
    0x48,  # [39] equal =
    0x08,  # [40] underscore _
    0x58,  # [41] lowercase 'c' normal
    0x61,  # [42] lowercase 'c' upper
    0x01,  # [43] tilde for top segment only
    0x41,  # [44] equals but high
    0x49,  # [45] three dash
    0x7E   # [46] W for WIFI
]

digitAddress = [
    0x68,       # 104
    0x6A,       # 106
    0x6C,       # 108
    0x6E        # 110
]

class LED4digdisp:
    def __init__(self, ID, clock=1, data=0):
        self.ID = ID
        self.clock_pin_no = clock
        self.data_pin_no = data
        self.displayDigitsRaw = [0, 0, 0, 0]
        self.pulse_width = DEFAULT_PULSE_WIDTH
        self.half_pulse_width = DEFAULT_HALF_PULSE_WIDTH
        self.reconfigure(self.clock_pin_no, self.data_pin_no)

    def reconfigure(self, clock_pin_no=1, data_pin_no=0):
        self.clock_pin = Pin(clock_pin_no, Pin.OUT)
        self.clock_pin.off()
        self.data_pin = Pin(data_pin_no, Pin.OUT)
        self.data_pin.off()
        self.send_idle_state()

    def set_pin_mode(self, pin_num, mode):
        return Pin(pin_num, mode)

    def set_speed(self, baud=8333):
        clock_length = 120                                      # default to 120 microseconds
        clock_length = 1000000 / baud
        if clock_length >= 4:
            self.pulse_width = int(clock_length / 2)
            self.half_pulse_width = int(clock_length / 4)
        else:
            self.pulse_width = DEFAULT_PULSE_WIDTH
            self.half_pulse_width = DEFAULT_HALF_PULSE_WIDTH

    def send_Start(self):
        self.data_pin.on()
        self.clock_pin.on()
        time.sleep_us(self.pulse_width)
        self.data_pin.off()
        time.sleep_us(self.pulse_width)
        self.clock_pin.off()

    def send_idle_state(self):
        self.clock_pin.on()
        time.sleep_us(self.pulse_width)
        self.data_pin.on()
        time.sleep_us(self.pulse_width)

    def display_on(self, brightness=0):
        self.send_idle_state()
        brightness &= 7
        brightness <<= 4
        brightness |= 1
        self.send_pair(DEFAULT_SYSTEM_COMMAND, brightness)

    def display_off(self):
        self.send_pair(DEFAULT_SYSTEM_COMMAND, 0)

    def display_clear(self):
        for i in range(4):
            self.send_pair(digitAddress[i], 0)
            self.displayDigitsRaw[i] = 0

    def show_segments(self, pos=0, pattern=0):
        pos &= 3
        self.displayDigitsRaw[pos] = pattern
        self.send_pair(digitAddress[pos], self.displayDigitsRaw[pos])

    def show_char(self, pos=0, c=0):
        char_index = 30
        pos &= 3
        char_index = self.char_to_index(c)
        if c == 0x2E:
            self.displayDigitsRaw[pos] |= 128
        else:
            self.displayDigitsRaw[pos] = characterBytes[char_index]
        #print(f"Sending segment byte 0x{self.displayDigitsRaw[pos]:02X} to address 0x{digitAddress[pos]:02X}")
        self.send_pair(digitAddress[pos], self.displayDigitsRaw[pos])

    def show_char_with_point(self, pos=0, c=0):
        char_index2 = 30
        pos &= 3
        char_index2 = self.char_to_index(c)
        self.displayDigitsRaw[pos] = characterBytes[char_index2] | 128
        self.send_pair(digitAddress[pos], self.displayDigitsRaw[pos])

    def show_string(self, s):
        outc = [0, 0, 0, 0]             # ascii codes of the 4 characters to display
        dp = [0, 0, 0, 0]               # flag as to whether a decimal point should be included for each character
        c = 0                           # temp value
        index = 0                       # input string index
        di = 0                          # output display index

        display_chars = 0               # character count excluding decimals
        trunc_output = ""               # temporary truncated string

        for ch in s:                            # Limit to maximum 4 displayable characters (not counting decimal points)
            if ch == '.':
                trunc_output += ch
            else:
                if display_chars >= 4:
                    break
                trunc_output += ch
                display_chars += 1
        
        s = trunc_output

        disp_char_count = sum(1 for ch in s if ch != '.')
        if disp_char_count < 4:                         # if the output is less than 4 characters (excluding decimal point)
            s = ' ' * (4 - disp_char_count) + s         # add blank spaces to pad the left side

        for index in range(len(s)):
            c = ord(s[index])                           # lookup ascii code of each character in the string 
            if c == 0x2E:                               # if the first character is a decimal point, 
                if di == 0:             
                    outc[di] = 32                       # add a space character with a decimal point to the output
                    dp[di] = 1
                    di += 1
                else:
                    if dp[di - 1] == 0:                 # if the previous char doesn’t have a decimal point, this decimal is added to it.
                        dp[di - 1] = 1
                    else:                               # otherwise, assign a decimal point to a blank space
                        dp[di] = 1          
                        di += 1
                        outc[di] = 32
            else:
                outc[di] = c                            # add character to the output buffer
                di += 1

        for index in range(di):
            c = outc[index]                             # send each individual character in the buffer to the display
            if dp[index] == 0:
                self.show_char(index, c)                # if it doesn't have a decimal, send it
            else:
                self.show_char_with_point(index, c)     # if it does have a decimal, send it with a decimal

    def show_integer(self, n= int(0)):
        outc2 = [32, 32, 32, 32]
        i = 3
        absn = 0
        if (n > 9999) or (n < -999):
            self.show_string("Err ")
        else:
            absn = abs(n)
            if absn == 0:
                outc2[3] = 0x30
            else:
                while absn != 0:
                    outc2[i] = (absn % 10) + 0x30
                    absn = absn // 10
                    i -= 1
                if n < 0:
                    outc2[i] = 0x2D
            for i in range(4):
                # print(outc2[i])
                self.show_char(i, outc2[i])

    def show_hex(self, n=0):
        j = 3

        if (n > 0xFFFF) or (n < -32768):
            self.show_string("Err ")
        else:
            for j in range(3):
                self.displayDigitsRaw[j] = 0
            self.displayDigitsRaw[3] = characterBytes[0]
            if n < 0:
                n = 0x10000 + n
            for j in range(3, -1, -1):
                self.displayDigitsRaw[j] = characterBytes[n & 15]
                n >>= 4
            for j in range(4):
                self.send_pair(digitAddress[j], self.displayDigitsRaw[j])

    def show_decimal(self, n=0):
        s = ""
        target_len = 4

        if (n > 9999) or (abs(n) < 0.001) or (n < -999):
            self.show_string("Err ")
        else:
            s = str(n)
            if "." in s:
                target_len = 4 - (len(s) - s.index("."))
                if target_len > 4:
                    target_len = 4
                if target_len < 0:
                    target_len = 0
            else:
                s += "."
            for _ in range(target_len):
                s += "0"
            self.show_string(s)
    
    def send_pair(self, d=0, v=0):
        self.send_Start()
        self.send_byte(d)
        self.send_byte(v)
        self.send_idle_state()

    def send_byte(self, data=0):
        bitMask = 0x80  # Start with MSB

        # Send 8 bits
        while bitMask:
            if data & bitMask:
                self.data_pin.on()
            else:
                self.data_pin.off()

            time.sleep_us(self.half_pulse_width)
            self.clock_pin.on()
            time.sleep_us(self.pulse_width)
            self.clock_pin.off()
            time.sleep_us(self.half_pulse_width)

            bitMask >>= 1

        # Prepare to receive ACK from TM1650
        self.data_pin.init(Pin.IN, Pin.PULL_UP)  # Release DATA pin
        time.sleep_us(self.half_pulse_width)
        self.clock_pin.on()
        time.sleep_us(self.half_pulse_width)

        ackBit = self.data_pin.value()  # TM1650 pulls low to ACK
        #print("ack:", ackBit)

        self.clock_pin.off()
        time.sleep_us(self.half_pulse_width)

        # Return DATA pin to output mode
        self.data_pin.init(Pin.OUT)
        self.data_pin.off()
        time.sleep_us(self.half_pulse_width)

        return ackBit
    
    def send_byte_original(self, data=0):
        bitMask = 128
        while bitMask != 0:
        # for _ in range(8):
        #   v = data & 1
        #   data >>= 1
        #   b <<= 1
        #   b |= v
        #   time.sleep_us(5)
            time.sleep_us(self.half_pulse_width)
            if (data & bitMask) == 0:
                self.data_pin.off()
            else:
                self.data_pin.on()
            time.sleep_us(self.half_pulse_width)
            self.clock_pin.on()
            time.sleep_us(self.pulse_width)
            self.clock_pin.off()
            bitMask >>= 1
        self.data_pin = self.set_pin_mode(self.data_pin_no, Pin.IN)
        time.sleep_us(self.pulse_width)
        self.clock_pin.on()
        time.sleep_us(self.pulse_width)
        ackBit = self.data_pin.value()
        #print("ack: ", ackBit)
        self.clock_pin.off()
        time.sleep_us(self.half_pulse_width)
        self.data_pin = self.set_pin_mode(self.data_pin_no, Pin.OUT)
        self.data_pin.off()
        time.sleep_us(self.half_pulse_width)

    def char_to_index_orig(self, c):
        char_code = 30
        if c < 30:
            char_code = c
        else:
            if 0x2F < c < 0x3A:
                char_code = c - 0x30
            else:
                if c > 0x40:
                    c &= 0xDF  # Uppercase
                if 0x40 < c < 0x4B:
                    char_code = c - 0x37
                else:
                    if c == 0x4C:
                        char_code = 20
                    if 0x4E <= c <= 0x52:
                        char_code = 21 + (c - 0x4E)
                    if c == 0x54:
                        char_code = 26
                    if c == 0x55:
                        char_code = 27
                    if c == 0x2D:
                        char_code = 28
                    if c == 0x2A:
                        char_code = 29
                    else:
                        char_code = 0
        return char_code
    
    def char_to_index(self, c):
        # If input is int (ASCII code), convert to string
        if isinstance(c, int):
            c = chr(c)

        # Handle custom specials first
        if c == "c":        # normal lowercase 'c'
            return 41
        if c == "^":        # top lowercase 'c'
            return 42
        if c == "*":        # degree symbol
            return 38
        if c == "~":        # top segment
            return 43
        if c == ">":        # equals but high
            return 44
        if c == "#":        # three dash
            return 45
        if c == "&":        # W for Wifi
            return 46

        # Digits 0–9
        if "0" <= c <= "9":
            return ord(c) - ord("0")

        # Letters A–Z
        if "A" <= c.upper() <= "Z":
            return 10 + (ord(c.upper()) - ord("A"))

        # Other special characters
        special_map = {
            " ": 36,
            "-": 37,
            "=": 39,
            "_": 40,
        }
        return special_map.get(c, 36)  # fallback to space
