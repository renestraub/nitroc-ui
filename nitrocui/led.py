import os

class LED_RGB():
    COLORS = {
        "off": "0 0 0",
        "red": "100 0 0",
        "green": "0 100 0",
        "blue": "0 0 100",
        "yellow": "100 10 0",
        "white": "100 100 100",
    }

    # Possible LED locations
    LED_PATHS = [
        "/sys/class/leds/ec:power/",
        "/sys/class/leds/chromeos:multicolor:power/",
    ]

    def __init__(self):
        super().__init__()

        # Determine the correct LED path by checking existence
        self.led_path = next((path for path in LED_RGB.LED_PATHS if os.path.exists(path)), None)
        if self.led_path:
            self.rgb_path = self.led_path + "multi_intensity"
            self.brightness_path = self.led_path + "brightness"
        else:
            self.rgb_path = None
            self.brightness_path = None

    def off(self) -> None:
        self._set("off")

    def red(self) -> None:
        self._set("red")

    def yellow(self) -> None:
        self._set("yellow")

    def green(self) -> None:
        self._set("green")

    def color(self, name) -> None:
        self._set(name)

    def _set(self, color) -> None:
        if color in LED_RGB.COLORS:
            rgb_color = LED_RGB.COLORS[color]

            if self.rgb_path:
                with open(self.rgb_path, 'w') as f:
                    f.write(rgb_color)
            if self.brightness_path:
                with open(self.brightness_path, 'w') as f:
                    f.write("100")
