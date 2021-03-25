# timer
from z80 import IF_TIMER
from utils import getBit
# addresses of registers
DIV_ADDR  = 0xFF04
TIMA_ADDR = 0xFF05
TMA_ADDR  = 0xFF06
TAC_ADDR  = 0xFF07

class Timer(object):

    DIVIDERS = (1024, 16, 64, 256)
    __slots__ = ('emu', 'divCounter', 'timaCounter')

    def __init__(self, emu) -> None:
        # reference of emulator
        self.emu = emu
        self.divCounter = 0
        self.timaCounter = 0
    
    def tick(self, cyclesPassed: int) -> None:
        # update the value of DIV
        div = self.emu.read(DIV_ADDR)
        self.divCounter += cyclesPassed
        div += self.divCounter >> 8
        self.divCounter &= 0xFF
        self.emu.write(DIV_ADDR, div & 0xFF)

        tac = self.emu.read(TAC_ADDR)
        # timer not enabled
        if getBit(tac, 2) == 0: return
        
        self.timaCounter += cyclesPassed
        divider = Timer.DIVIDERS[getBit(tac, 0, bit2=True)]
        tima = self.emu.read(TIMA_ADDR)

        if self.timaCounter >= divider:
            self.timaCounter -= divider
            tima += 1
            if tima > 0xFF:
                tima = self.emu.read(TMA_ADDR) & 0xFF
                self.emu.write(TIMA_ADDR, tima)
                self.emu.z80.setInterrupt(IF_TIMER)
            else:
                self.emu.write(TIMA_ADDR, tima)
    
    def cycles2interrupt(self) -> int:
        tac = self.emu.read(TAC_ADDR)
        if getBit(tac, 2):
            divider = Timer.DIVIDERS[getBit(tac, 0, bit2=True)]
            cyclesLeft = ((0x100 - self.emu.read(TIMA_ADDR)) * divider) - self.timaCounter
            return cyclesLeft
        else:
            # timer not enabled, return a large enough value
            return 1 << 16
