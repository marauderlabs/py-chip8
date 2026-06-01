import pygame

DEFAULT_KEYMAP = {
    pygame.K_1: 0x1, pygame.K_2: 0x2, pygame.K_3: 0x3, pygame.K_4: 0xC,
    pygame.K_q: 0x4, pygame.K_w: 0x5, pygame.K_e: 0x6, pygame.K_r: 0xD,
    pygame.K_a: 0x7, pygame.K_s: 0x8, pygame.K_d: 0x9, pygame.K_f: 0xE,
    pygame.K_z: 0xA, pygame.K_x: 0x0, pygame.K_c: 0xB, pygame.K_v: 0xF,
}

class Input:
    def __init__(self, keymap: dict[int, int] | None = None) -> None:
        self.keymap = keymap or DEFAULT_KEYMAP
        self._pressed = set()
        self._just_pressed: int | None = None

    def update(self, events: list[pygame.event.Event]) -> None:
        self._just_pressed = None
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in self.keymap:
                chip8_key = self.keymap[event.key]
                if chip8_key not in self._pressed:
                    self._just_pressed = chip8_key
                self._pressed.add(chip8_key)
            elif event.type == pygame.KEYUP and event.key in self.keymap:
                self._pressed.discard(self.keymap[event.key])

    def is_pressed(self, key: int) -> bool:
        return key in self._pressed

    def get_just_pressed(self) -> int | None:
        key = self._just_pressed
        self._just_pressed = None
        return key
