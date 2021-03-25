# utility funcions

def toHex(byte: int, length: int=2) -> str:
    return hex(byte)[2:].zfill(length).upper()

def getBit(byte: int, offset: int, bit2: bool=False) -> int:
    return (byte >> offset) & (3 if bit2 else 1)

def setBit(byte: int, offset: int, val: int, bit2: bool=False) -> int:
    byte &= ~((3 if bit2 else 1) << offset) & 0xFF
    byte |= val << offset
    return byte

def decodeColor(byte1: int, byte2: int, offset: int) -> int:
    # The colors are 2 bit and are found like this:
    # Color of the first pixel is 0b10
    # | Color of the second pixel is 0b01
    # v v
    # 1 0 0 1 0 0 0 1 < - byte1
    # 0 1 1 1 1 1 0 0 < - byte2
    offset = 7 - offset
    return getBit(byte2, offset) << 1 | getBit(byte1, offset)

COLORS = [
    # WHITE     LIGHT     DARK      BLACK
    (0xFFFFFF, 0xB2B2B2, 0x666666, 0x000000),
    (0x9BBC0F, 0x8BAC0F, 0x306230, 0x0F380F)
]
def getColor(colorCode: int, nostalgic: bool) -> int:
    return COLORS[int(nostalgic)][colorCode]

class Tile(object):

    ROWS, COLS = 8, 8
    BGP_ADDR = 0xFF47

    def __init__(self, emu, addr: int) -> None:
        self.palette = emu.read(self.BGP_ADDR)
        self.pixels = [[0] * self.COLS for _ in range(self.ROWS)]
        self.initPixels(emu, addr)

    def initPixels(self, emu, addr: int) -> None:
        for y in range(self.ROWS):
            dst = addr + y * 2
            byte1 = emu.read(dst)
            byte2 = emu.read(dst + 1)
            for x in range(self.COLS):
                colorIdx = decodeColor(byte1, byte2, x)
                self.pixels[y][x] = getBit(self.palette, colorIdx * 2, bit2=True)

class SpriteTile(object):

    ROWS, COLS = 8, 8
    OBP0_ADDR = 0xFF48
    OBP1_ADDR = 0xFF49

    def __init__(self, emu, addr: int) -> None:
        self.y = emu.read(addr) - 16
        self.x = emu.read(addr + 1) - 8

        flags = emu.read(addr + 3)
        self.palette = emu.read(self.OBP1_ADDR) if flags & 0x10 else emu.read(self.OBP0_ADDR)
        self.xFlip = bool(flags & 0b00100000)
        self.yFlip = bool(flags & 0b01000000)
        self.priority = flags & 0b10000000 != 0x80

        self.pixels = [[0] * self.COLS for _ in range(self.ROWS)]

    def initPixels(self, emu, selectFunc) -> None:
        for y in range(self.ROWS):
            dst = 0x8000 + selectFunc(y) * 0x10 + y * 2
            byte1 = emu.read(dst)
            byte2 = emu.read(dst + 1)
            for x in range(self.COLS):
                colorIdx = decodeColor(byte1, byte2, x)
                self.pixels[y][x] = getBit(self.palette, colorIdx * 2, bit2=True) if colorIdx else -1

    def flipPixels(self) -> None:
        if self.xFlip:
            self.pixels = [row[::-1] for row in self.pixels]
        if self.yFlip:
            self.pixels = self.pixels[::-1]

class SpriteTile8(SpriteTile):

    def __init__(self, emu, addr: int) -> None:
        super().__init__(emu, addr)

        self.idx = emu.read(addr + 2)

        self.initPixels(emu, lambda y: self.idx)
        self.flipPixels()

class SpriteTile16(SpriteTile):

    def __init__(self, emu, addr: int) -> None:
        SpriteTile16.ROWS = 16
        super().__init__(emu, addr)
        idx = emu.read(addr + 2)
        self.lower = idx | 0x01
        self.upper = idx & 0xFE

        self.initPixels(emu, lambda y: self.lower if y > 7 else self.upper)
        self.flipPixels()
