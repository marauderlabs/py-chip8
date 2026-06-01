import random
from .display import Display
from .input import Input

# 16x5 bytes font data for hexadecimal digits 0-F, stored in the first 80 bytes of memory
# Refer: https://craigthomas.ca/blog/2017/10/15/writing-a-chip-8-emulator-built-in-font-set-part-4/
FONT_DATA = bytes([
    0xF0,0x90,0x90,0x90,0xF0, # 0
    0x20,0x60,0x20,0x20,0x70, # 1
    0xF0,0x10,0xF0,0x80,0xF0, # 2
    0xF0,0x10,0xF0,0x10,0xF0, # 3
    0x90,0x90,0xF0,0x10,0x10, # 4
    0xF0,0x80,0xF0,0x10,0xF0, # 5
    0xF0,0x80,0xF0,0x90,0xF0, # 6
    0xF0,0x10,0x20,0x40,0x40, # 7
    0xF0,0x90,0xF0,0x90,0xF0, # 8
    0xF0,0x90,0xF0,0x10,0xF0, # 9
    0xF0,0x90,0xF0,0x90,0x90, # A
    0xE0,0x90,0xE0,0x90,0xE0, # B
    0xF0,0x80,0x80,0x80,0xF0, # C
    0xE0,0x90,0x90,0x90,0xE0, # D
    0xF0,0x80,0xF0,0x80,0xF0, # E
    0xF0,0x80,0xF0,0x80,0x80, # F
])

class CPU:
    MEMORY_SIZE = 4096
    ROM_START = 0x200 # Programs are loaded at 0x200 (512 in decimal)

    def __init__(self, display, input_device):
        self.display = display
        self.input = input_device
        self.memory = bytearray(self.MEMORY_SIZE)
        self.v = [0] * 16        # registers V0–VF
        self.i = 0               # index register
        self.pc = self.ROM_START
        self.stack = []          # TBD: Mimic actual interpreter
        self.delay_timer = 0
        self.sound_timer = 0
        self.memory[:len(FONT_DATA)] = FONT_DATA # Font data is stored in the first 80 bytes
        self._dispatch = {
            0x1000: self._op_1,
            0x6000: self._op_6,
            0x7000: self._op_7,
        }

    # https://craigthomas.ca/blog/2014/07/17/writing-a-chip-8-emulator-part-2/
    def _op_1(self, opcode):
        # 1nnn - Jump to address nnn
        address = opcode & 0x0FFF
        self.pc = address

    def _op_6(self, opcode):
        # 6snn - Load register s with value nn
        register = (opcode & 0x0F00) >> 8
        value = opcode & 0x00FF
        self.v[register] = value

    def _op_7(self, opcode):
        # 7snn - Add value nn to register s
        register = (opcode & 0x0F00) >> 8
        value = opcode & 0x00FF
        self.v[register]  = (self.v[register] + value) & 0xFF
        # No carry. carry handled by 8st4

    def _get_dispatcher(self, opcode):
        handler = self._dispatch.get(opcode & 0xF000)
        if handler is None:
            raise ValueError(f"Unknown opcode: {opcode:04X}")
        return handler

    def load_rom(self, data: bytes):
        self.memory[self.ROM_START:self.ROM_START + len(data)] = data

    def step(self):
        # Fetch the next opcode (2 bytes) and increment the program counter
        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2
        handler = self._get_dispatcher(opcode)
        handler(opcode)

    def tick_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
