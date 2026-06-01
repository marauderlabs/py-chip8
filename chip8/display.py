class Display():
    WIDTH=64
    HEIGHT=32
    def __init__(self):
        self.clear()

    def clear(self) -> None:
        self._pixels = [[False] * (self.WIDTH) for y in range(self.HEIGHT)]

    def xor_pixel(self, x, y: int) -> bool:
        if x >= self.WIDTH or y >= self.HEIGHT:
            return False

        self._pixels[y][x] = not self._pixels[y][x]
        return not self._pixels[y][x]

    def get_pixels(self) -> list[list[bool]]:
        return self._pixels
