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
        self.v = [0] * 16        # 8-bit registers V0–VF
        self.i = 0               # 12-bit index register
        self.pc = self.ROM_START
        self.stack = []          # TBD: Mimic actual interpreter
        self.delay_timer = 0
        self.sound_timer = 0
        self.memory[:len(FONT_DATA)] = FONT_DATA # Font data is stored in the first 80 bytes
        self._dispatch = {
            0x0000: self._op_0,
            0x1000: self._op_1,
            0x2000: self._op_2,
            0x3000: self._op_3,
            0x4000: self._op_4,
            0x5000: self._op_5,
            0x6000: self._op_6,
            0x7000: self._op_7,
            0x8000: self._op_8,
            0x9000: self._op_9,
            0xA000: self._op_A,
            0xB000: self._op_B,
            0xC000: self._op_C,
            0xD000: self._op_D,
            0xE000: self._op_E,
            0xF000: self._op_F,
        }

    def _return_from_routine(self):
        # Deliberately not check empty stack
        self.pc = self.stack.pop()

    def _call_subroutine(self, addr):
        self.stack.append(self.pc)
        self.pc = addr

    def _next_instruction(self):
        self.pc += 2

    # https://craigthomas.ca/blog/2014/07/17/writing-a-chip-8-emulator-part-2/
    def _op_0(self, opcode):
        # 00E0 - Clear the screen
        # 00EE - Return from subroutine
        subcode = opcode & 0x00FF
        if subcode == 0xE0:
            self.display.clear()
        elif subcode == 0xEE:
            self._return_from_routine()
        else:
            raise ValueError(f"Unknown (00xx) opcode: {opcode:04X}")

    def _op_1(self, opcode):
        # 1nnn - Jump to address nnn
        address = opcode & 0x0FFF
        self.pc = address

    def _op_2(self, opcode):
        # 2nnn - Call routine at address nnn
        addr = opcode & 0x0FFF
        self._call_subroutine(addr)

    def _op_3(self, opcode):
        # 3snn - Skip next instruction if register s value equals nn
        register = (opcode & 0x0F00) >> 8
        value = opcode & 0x00FF
        if value == self.v[register]:
            self.pc += 2

    def _op_4(self, opcode):
        # 4snn - Do not skip next instruction if register s value equals nn
        register = (opcode & 0x0F00) >> 8
        value = opcode & 0x00FF
        if value != self.v[register]:
            self._next_instruction()

    def _op_5(self, opcode):
        # 5st0 - Skip if register s value equals register t value
        if opcode & 0xF != 0:
            raise ValueError(f"Unknown (5st0) opcode: {opcode:04X} ")
        s = (opcode & 0x0F00) >> 8
        t = (opcode & 0x00F0) >> 4
        if self.v[s] == self.v[t]:
            self._next_instruction()

    def _op_8(self, opcode):
        # 8stx - Arithmetic ops
        subcode = opcode & 0xF
        s = (opcode & 0x0F00) >> 8
        t = (opcode & 0x00F0) >> 4

        # 8st0 - Move value from register s to register t
        if subcode == 0:
            self.v[t] = self.v[s]
        # 8st1 - Perform logical OR on register s and t and store in t
        elif subcode == 1:
            self.v[t] |= self.v[s]
        # 8st2 - Perform logical AND on register s and t and store in t
        elif subcode == 2:
            self.v[t] &= self.v[s]
        # 8st3 - Perform logical XOR on register s and t and store in t
        elif subcode == 3:
            self.v[t] ^= self.v[s]
        # 8st4 - Add s to t and store in s - register F set on carry
        elif subcode == 4:
            self.v[s] += self.v[t]
            self.v[0xF] = self.v[s] >> 8
            self.v[s] &= 0xFF
        # 8st5 - Subtract s from t and store in s - register F set on no-borrow
        elif subcode == 5:
            self.v[0xF] = 1 if self.v[s] >= self.v[t] else 0
            self.v[s] = (self.v[s] - self.v[t]) & 0xFF
        # 8s06 - Shift bits in register s 1 bit to the right - bit 0 shifts to register F
        elif subcode == 6:
            self.v[0xF] = self.v[s] & 0x1
            self.v[s] >>= 1
        # 8st7 - same logic as 8st5 but operands swapped
        elif subcode == 7:
            self.v[0xF] = 1 if self.v[t] >= self.v[s] else 0
            self.v[s] = (self.v[t] - self.v[s]) & 0xFF
        # 8s0E - Shift bits in register s 1 bit to the left - bit 7 shifts to register F
        elif subcode == 0XE:
            self.v[0xF] = (self.v[s] & 0b1000_0000) >> 7
            self.v[s] <<= 1
            self.v[s] &= 0xFF
        else:
            raise ValueError(f"Unknown (8stx) opcode: {opcode:04X}")

    def _op_9(self, opcode):
        # 9st0 - Skip next instruction if register s not equal register t
        if opcode & 0xF != 0:
            raise ValueError(f"Unknown (9st0) opcode: {opcode:04X}")
        s = (opcode & 0x0F00) >> 8
        t = (opcode & 0x00F0) >> 4
        if self.v[s] != self.v[t]:
            self._next_instruction()

    def _op_A(self, opcode):
        # Annn - Load index with value nnn
        value = opcode & 0x0FFF
        self.i = value

    def _op_B(self, opcode):
        # Bnnn - Jump to address nnn + index
        self.pc = (opcode & 0x0FFF) + self.i

    def _op_C(self, opcode):
        # Ctnn - Sets register t to the result of a bitwise and operation on a random number (Typically: 0 to 255) and NN
        operand = opcode & 0x00FF
        register = (opcode & 0x0F00) >> 8
        self.v[register] = random.randint(0, 255) & operand

    def _op_D(self, opcode):
        # Dstn - Draw n byte sprite at x location reg s, y location reg t
        s = (opcode & 0x0F00) >> 8
        t = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F
        x, y = self.v[s], self.v[t]
        self.v[0xF] = 0 # reset flag reg
        for row in range(n):
            y_pos = y + row
            if y_pos >= self.display.HEIGHT or self.i + row >= self.MEMORY_SIZE:
                break

            sprite_byte = self.memory[self.i + row]
            for bit in range(8):
                x_pos = x + bit
                if x_pos >= self.display.WIDTH:
                    break
                if sprite_byte & (0x80 >> bit):
                    if self.display.xor_pixel(x_pos, y_pos):
                        self.v[0xF] = 1

    def _op_E(self, opcode):
        #Ex9E — skip if key V[x] is currently pressed
        #ExA1 — skip if key V[x] is not pressed
        register = (opcode & 0x0F00) >> 8
        subcode = opcode & 0x00FF
        key = self.v[register]
        if subcode == 0x9E:
            if self.input.is_pressed(key):
                self._next_instruction()
        elif subcode == 0xA1:
            if not self.input.is_pressed(key):
                self._next_instruction()
        else:
            raise ValueError(f"Unknown (Exxx) opcode: {opcode:04x}")

    def _op_F(self, opcode):
        register = (opcode & 0x0F00) >> 8
        subcode = opcode & 0x00FF

        # Fx07 — V[x] = delay_timer
        if subcode == 0x07:
            self.v[register] = self.delay_timer
        # Fx0A — wait for keypress, store in V[x] (blocking)
        elif subcode == 0x0A:
            key_pressed = False
            while not key_pressed:
                for key in range(16):
                    if self.input.is_pressed(key):
                        self.v[register] = key
                        key_pressed = True
                        break
        # Fx15 — delay_timer = V[x]
        elif subcode == 0x15:
            self.delay_timer = self.v[register]
        # Fx18 — sound_timer = V[x]
        elif subcode == 0x18:
            self.sound_timer = self.v[register]
        # Fx1E — I += V[x]
        elif subcode == 0x1E:
            self.i += self.v[register]
        # Fx29 — I = font address for digit V[x] (each font char is 5 bytes, starts at 0)
        elif subcode == 0x29:
            digit = self.v[register]
            self.i = digit*5
        # Fx33 — store BCD of V[x] at I, I+1, I+2
        elif subcode == 0x33:
            # Splits a number like 156 into three digits: hundreds=1, tens=5, ones=6 — stored at I, I+1, I+2:
            val = self.v[register]
            self.memory[self.i]     = val // 100
            self.memory[self.i + 1] = (val % 100) // 10
            self.memory[self.i + 2] = val % 10
        # Fx55 — store V[0]–V[x] in memory starting at I
        elif subcode == 0x55:
            for n in range(register + 1):
                self.memory[self.i + n] = self.v[n]
        # Fx65 — read memory starting at I into V[0]–V[x]
        elif subcode == 0x65:
            for n in range(register + 1):
                self.v[n] = self.memory[self.i +n]
        else:
            raise ValueError(f"Unknown (Fxxx) opcode: {opcode:04x}")


    def _op_6(self, opcode):
        # 6snn - Load register s with value nn
        register = (opcode & 0x0F00) >> 8
        value = opcode & 0x00FF
        self.v[register] = value

    def _op_7(self, opcode):
        # 7snn - Add value nn to register s
        register = (opcode & 0x0F00) >> 8
        value = opcode & 0x00FF
        self.v[register] = (self.v[register] + value) & 0xFF
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
        self._next_instruction()
        handler = self._get_dispatcher(opcode)
        handler(opcode)

    def tick_timers(self):
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
