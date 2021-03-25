# mother board
from z80 import Z80
from ppu import INSTRUCTION, PPU
from mmu import MMU
from timer import Timer
from utils import toHex

class Emulator(object):

    __slots__ = (
        'z80', 'ppu', 'mmu', 'timer',
        'LOG', 'frames', 'paused'
    )

    def __init__(self, rom: str, skipBios: bool=False, nostalgic: bool=False) -> None:
        # main units
        self.z80 = Z80(self)
        self.ppu = PPU(self, nostalgic)
        self.mmu = MMU(self, rom)
        self.timer = Timer(self)
        # log dict
        self.LOG = {}
        # global states
        self.frames = 0
        self.paused = False

        self.initData(skipBios)
        print(INSTRUCTION)
    
    def step(self) -> None:
        if self.mmu.dmaInProgress:
            cyclesPassed = self.mmu.step()
        else:
            cyclesPassed = self.z80.step()
        self.takeLog()
        self.timer.tick(cyclesPassed)
        self.ppu.tick(cyclesPassed)
    
    def run(self, frames: int=-1) -> None:
        while self.frames != frames:
            self.step()
            '''
            if self.paused:
                self.ppu.delay(100)
            else:
                self.tick()
                self.ppu.updateLCD()
                self.frames += 1
            self.ppu.handleEvents()
            '''
    
    def read(self, addr: int) -> int:
        return self.mmu.read(addr)

    def write(self, addr: int, byte: int) -> None:
        self.mmu.write(addr, byte)
    
    def initData(self, skipBios: bool) -> None:
        if not skipBios: return

        self.z80.PC = 0x100
        self.z80.SP = 0xFFFE
        self.z80.A = 0x01
        self.z80.B = 0x00
        self.z80.C = 0x13
        self.z80.D = 0x00
        self.z80.E = 0xD8
        self.z80.F = 0xB0
        self.z80.H = 0x01
        self.z80.L = 0x4D

        self.write(0xFF10, 0x80)
        self.write(0xFF11, 0xBF)
        self.write(0xFF12, 0xF3)
        self.write(0xFF14, 0xBF)
        self.write(0xFF16, 0x3F)
        self.write(0xFF19, 0xBF)
        self.write(0xFF1A, 0x7F)
        self.write(0xFF1B, 0xFF)
        self.write(0xFF1C, 0x9F)
        self.write(0xFF1E, 0xBF)
        self.write(0xFF20, 0xFF)
        self.write(0xFF23, 0xBF)
        self.write(0xFF24, 0x77)
        self.write(0xFF25, 0xF3)
        self.write(0xFF26, 0xF1)
        self.write(0xFF40, 0x91)
        self.write(0xFF41, 0x05)
        self.write(0xFF47, 0xFC)
        self.write(0xFF48, 0xFF)
        self.write(0xFF49, 0xFF)
        self.write(0xFF50, 0x01)
    
    def takeLog(self) -> None:
        self.LOG['frames'] = self.frames
        self.LOG['opcode'] = toHex(self.z80.opcode)
        self.LOG['opname'] = self.z80.opname

        self.LOG['arg0'] = toHex(self.z80.args[0])
        self.LOG['arg1'] = toHex(self.z80.args[1])

        self.LOG['PC'] = toHex(self.z80.PC, 4)
        self.LOG['SP'] = toHex(self.z80.SP, 4)

        self.LOG['A'] = toHex(self.z80.A)
        self.LOG['B'] = toHex(self.z80.B)
        self.LOG['C'] = toHex(self.z80.C)
        self.LOG['D'] = toHex(self.z80.D)
        self.LOG['E'] = toHex(self.z80.E)
        self.LOG['F'] = toHex(self.z80.F)
        self.LOG['H'] = toHex(self.z80.H)
        self.LOG['L'] = toHex(self.z80.L)

    def printReg(self) -> None:
        print('\nregisters:')
        for key, val in self.LOG.items():
            print('\t', key, val)

    def printMem(self, title: str, start: int, stop: int, step: int) -> None:
        print(title)
        for addr in range(start, stop, step):
            print(f'\t{toHex(addr, length=4)}', end='    ')
            for offset in range(step):
                print(toHex(self.read(addr + offset)), end=' ')
            print()
