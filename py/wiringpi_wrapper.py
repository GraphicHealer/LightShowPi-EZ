class WiringpiWrapper:
    def __init__(self, virtual_pins=False):
        self._virtual_pins = virtual_pins

        if not self.is_virtual_pins():
            import wiringpi2
            self._wiringpi2 = wiringpi2

    def is_virtual_pins(self):
        return self._virtual_pins

    def _wrap_void(self, method, *args):
        if not self.is_virtual_pins():
            getattr(self._wiringpi2, method)(*args)

    # TODO - Find a way to "method_missing" all of this...

    # Setup
    def wiringPiSetup(self, *args):
        self._wrap_void("wiringPiSetup", *args)

    def wiringPiSetupSys(self, *args):
        self._wrap_void("wiringPiSetupSys", *args)

    def pinMode(self, *args):
        self._wrap_void("pinMode", *args)

    # Pin Writes
    def softPwmCreate(self, *args):
        self._wrap_void("softPwmCreate", *args)

    def softPwmWrite(self, *args):
        self._wrap_void("softPwmWrite", *args)

    def digitalWrite(self, *args):
        self._wrap_void("digitalWrite", *args)

    # Devices
    def mcp23017Setup(self, *args):
        self._wrap_void("mcp23017Setup", *args)

    def mcp23s17Setup(self, *args):
        self._wrap_void("mcp23s17Setup", *args)

    def mcp23016Setup(self, *args):
        self._wrap_void("mcp23016Setup", *args)

    def mcp23008Setup(self, *args):
        self._wrap_void("mcp23008Setup", *args)

    def mcp23s08Setup(self, *args):
        self._wrap_void("mcp23s08Setup", *args)

    def sr595Setup(self, *args):
        self._wrap_void("sr595Setup", *args)

    def pcf8574Setup(self, *args):
        self._wrap_void("pcf8574Setup", *args)

