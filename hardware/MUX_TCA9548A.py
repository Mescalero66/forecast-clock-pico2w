from machine import I2C, Pin

class I2CMultiplex:
    def __init__(self, addr, I2Cbus, scl_pin=1, sda_pin=0, freq=400000):
        """
        addr: I2C address of the multiplexer
        scl_pin, sda_pin: Pico pin numbers for I2C
        freq: I2C clock speed (default 400kHz)
        """
        self.i2c = I2C(I2Cbus, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
        self.addr = addr

    def scan(self, port):
        """
        Scan all I2C devices connected to the selected multiplexer port.
        """
        buf = []
        self.select_port(port)
        for address in range(0x03, 0x78):  # skip reserved addresses
            if address == self.addr:
                continue
            try:
                self.i2c.writeto(address, b"")
                buf.append(address)
            except OSError:
                pass
        return buf

    def select_port(self, port):
        """
        Enable a specific channel (0-7) on the I2C multiplexer, or 8 to disable all.
        """
        if port > 8:
            return
        try:
            if port == 8:
                data = 0x00  # disable all channels
            else:
                data = (1 << port) & 0xFF
            self.i2c.writeto(self.addr, bytes([data]))
        except OSError:
            print("Internal mux port select error.")

    def writeto_mem(self, port, addr, reg, buf):
        """
        Write a buffer to a device register.
        """
        self.select_port(port)
        if isinstance(buf, int):
            buf = bytes([buf])
        elif isinstance(buf, list):
            buf = bytes(buf)
        self.i2c.writeto_mem(addr, reg, buf)

    def readfrom_mem(self, port, addr, reg, nbytes):
        """
        Read nbytes from a device register.
        """
        self.select_port(port)
        return self.i2c.readfrom_mem(addr, reg, nbytes)
