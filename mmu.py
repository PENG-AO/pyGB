# memory management unit

# General Memory Map
# Start End     Description                      Notes
# 0000  3FFF    16KB ROM bank 00                 From cartridge, usually a fixed bank
# 4000  7FFF    16KB switchable ROM Bank         From cartridge, switchable bank via MBC (if any)
# 8000  9FFF    8KB Video RAM (VRAM)             Only bank 0 in Non-CGB mode
# A000  BFFF    8KB switchable RAM Bank          In cartridge, switchable bank (if any)
# C000  DFFF    8KB internal RAM
# E000  FDFF    Mirror of C000~DDFF (ECHO RAM) 	 Typically not used
# FE00  FE9F    Sprite attribute table (OAM)
# FEA0  FEFF    Not Usable
# FF00  FF7F    special I/O Registers
# FF80  FFFE    internal RAM
# FFFF  FFFF    Interrupts Enable Register (IE)

from utils import toHex
# addresses of registers
P1_ADDR   = 0xFF00
DMA_ADDR  = 0xFF46
BOOT_ADDR = 0xFF50

class MMU(object):

    __slots__ = (
        'emu', 'bytes', 'rom',
        'dmaInProgress', 'dmaSetDelay', 'dmaCounter'
    )
    
    def __init__(self, emu, rom: str) -> None:
        # reference of emulator
        self.emu = emu
        # memory
        self.bytes = bytearray(0x10000)
        bios = bytearray(open('./bios.gb', 'rb').read())
        for addr in range(0x100):
            self.bytes[addr] = bios[addr]
        self.rom = bytearray(open(rom, 'rb').read())
        for addr in range(0x100, 0x8000):
            self.bytes[addr] = self.rom[addr]
        # DMA transfer
        self.dmaInProgress = False
        self.dmaSetDelay = False
        self.dmaCounter = 0
    
    def read(self, addr: int) -> int:
        assert addr < 0x10000, f'!!! invalid address {toHex(addr, length=4)} !!!'

        if 0xE000 <= addr < 0xFE00:
            # echo of internal RAM (≈8KB)
            return self.read(addr - 0x2000)
        
        return self.bytes[addr]
    
    def write(self, addr: int, byte: int) -> None:
        assert addr < 0x10000, f'!!! invalid address {toHex(addr, length=4)} !!!'
        # assert addr > 0xFF, f'!!! unable to write {byte} to addr {toHex(addr, length=4)} !!!'

        if 0xE000 <= addr < 0xFE00:
            # echo of internal RAM (≈8KB)
            self.write(addr - 0x2000, byte)
        elif addr == P1_ADDR:
            # buttons
            byte = self.emu.ppu.pullButton(byte)
        elif addr == DMA_ADDR:
            # DMA
            self.requestDmaTransfer()
            print(f'from {toHex(byte)}00 to FE00 (DMA)')
        elif addr == BOOT_ADDR:
            # boot off
            self.remap2rom(byte)
        
        self.bytes[addr] = byte
    
    def requestDmaTransfer(self) -> None:
        self.dmaInProgress = True
        self.dmaSetDelay = True
        self.dmaCounter = 0
    
    #   ld (0x46), a ; start dma transfer
    #   ld a, 0x28   ; set counter and delay 8 cycles
    # wait:
    #   dec a        ; 1 cycles
    #   jr nz, wait  ; 4 cycles
    def step(self) -> int:
        if self.dmaSetDelay:
            self.dmaSetDelay = False
            return 8
        else:
            src = self.read(DMA_ADDR) << 8 + self.dmaCounter
            dst = 0xFE00 + self.dmaCounter
            self.write(dst, self.read(src))
            self.dmaCounter += 1
            if self.dmaCounter == 0xA0:
                self.dmaInProgress = False
            return 20

    def remap2rom(self, byte: int) -> None:
        if self.bytes[BOOT_ADDR] ^ byte:
            for addr in range(0x100):
                self.bytes[addr] = self.rom[addr]
