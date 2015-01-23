import os

class WiringPiStub:
    @classmethod
    def import_wiringpi2(cls, logger):
        is_pi = "raspberrypi" in os.uname()
        if is_pi:
            cls._is_stubbed = False
            logger.info("Raspberry Pi detected, enabling wiringpi2 library")
            import wiringpi2
            return wiringpi2
        else:
            cls._is_stubbed = True
            logger.info("Not running on the Raspberry Pi, using WiringPiStub")
            return WiringPiStub(logger)

    @classmethod
    def is_stubbed(cls):
      return cls._is_stubbed

    def __init__(self, logger):
        self._logger = logger

    # TODO - Find a way to "method_missing" all of this...

    # Setup
    def wiringPiSetup(self, *args):
        pass

    def wiringPiSetupSys(self, *args):
        pass

    def pinMode(self, *args):
        pass

    # Pin Writes
    def softPwmCreate(self, *args):
        pass

    def softPwmWrite(self, *args):
        pass

    def digitalWrite(self, *args):
        pass

    # Devices
    def mcp23017Setup(self, *args):
        pass

    def mcp23s17Setup(self, *args):
        pass

    def mcp23016Setup(self, *args):
        pass

    def mcp23008Setup(self, *args):
        pass

    def mcp23s08Setup(self, *args):
        pass

    def sr595Setup(self, *args):
        pass

    def pcf8574Setup(self, *args):
        pass

