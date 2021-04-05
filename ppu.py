# picture processing unit
import pygame, sys, os, time
from z80 import IF_STAT, IF_VBLANK
from utils import getBit, setBit, getColor, Tile, SpriteTile8, SpriteTile16, toHex

# instruction
INSTRUCTION = '''
    Instructions of pyGB gameboy emulator:

        Basic operations:
            Press   Key-RIGHT     for →
                    Key-LEFT      for ←
                    Key-UP        for ↑
                    Key-DOWN      for ↓
                    
                    Key-Z         for A
                    Key-X         for B
                    Key-BACKSPACE for SELECT
                    Key-RETURN    for START

        Additional functions:
            Press   Key-H for help

                    Key-Q to quit
                    Key-P to pause
                    Key-S to save screenshot
                    Key-C to clear outputs

                    Key-R to print registers
                    Key-M & 1 to print tile field 1 (0x8000 ~ 0x9000)
                    Key-M & 2 to print tile field 2 (0x8800 ~ 0x9800)
                    Key-M & 3 to print map  field 1 (0x9800 ~ 0x9C00)
                    Key-M & 4 to print map  field 2 (0x9C00 ~ 0xA000)
                    Key-M & 5 to print OAM(obj attr)(0xFE00 ~ 0xFEA0)
                    Key-M & 6 to print FF registers (0xFF00 ~ 0x10000)
'''
# path to save screenshots
SCREENSHOT_PATH = './screenshots'
# basic info of screen
ROWS, COLS, RESIZE = 144, 160, 3
# addresses of registers
LCDC_ADDR = 0xFF40
STAT_ADDR = 0xFF41
SCY_ADDR  = 0xFF42
SCX_ADDR  = 0xFF43
LY_ADDR   = 0xFF44
LYC_ADDR  = 0xFF45
WY_ADDR   = 0xFF4A
WX_ADDR   = 0xFF4B
# LCDC
LCDC_BG_EN    = 0
LCDC_OBJ_EN   = 1
LCDC_OBJ_SIZE = 2
LCDC_BG_MAP   = 3
LCDC_TILE_SEL = 4
LCDC_WIN_EN   = 5
LCDC_WIN_MAP  = 6
LCDC_LCD_EN   = 7
# STAT
STAT_LCD_MODE = 0
STAT_LYC_STAT = 2
STAT_INTR_M0  = 3
STAT_INTR_M1  = 4
STAT_INTR_M2  = 5
STAT_INTR_LYC = 6

class PPU(object):
    # LCD modes
    H_BLANK_MODE = 0
    V_BLANK_MODE = 1
    OAM_READ_MODE = 2
    VRAM_READ_MODE = 3
    # lasting cycles of each mode
    H_BLANK_TIME = 204
    V_BLANK_TIME = 456
    OAM_SCANLINE_TIME = 80
    VRAM_SCANLINE_TIME = 172
    # option
    NOSTALGIC = False

    __slots__ = (
        'emu',
        'LCD', 'buffer', 'cache',
        'scx', 'scy', 'clk',
        'dir', 'std'
    )

    def __init__(self, emu, nostalgic: bool) -> None:
        # reference of emulator
        self.emu = emu
        # main screen
        pygame.init()
        self.LCD = pygame.display.set_mode((COLS * RESIZE, ROWS * RESIZE), pygame.DOUBLEBUF)
        self.buffer = pygame.Surface((256 * RESIZE, 256 * RESIZE))
        self.cache = bytearray((0xFF,) * 0x400)
        self.scx, self.scy = 0, 0
        self.clk = 0
        # key input
        self.dir, self.std = 0xF, 0xF
        # set color option
        PPU.NOSTALGIC = nostalgic
    
    def tick(self, cyclesPassed: int) -> None:
        if getBit(self.emu.read(LCDC_ADDR), LCDC_LCD_EN):
            mode = getBit(self.emu.read(STAT_ADDR), STAT_LCD_MODE, bit2=True)
            self.clk += cyclesPassed
            if mode == PPU.OAM_READ_MODE:

                if self.clk >= PPU.OAM_SCANLINE_TIME:
                    self.clk -= PPU.OAM_SCANLINE_TIME
                    self.updateMode(PPU.VRAM_READ_MODE)
                
            elif mode == PPU.VRAM_READ_MODE:

                if self.clk >= PPU.VRAM_SCANLINE_TIME:
                    self.clk -= PPU.VRAM_SCANLINE_TIME
                    self.updateMode(PPU.H_BLANK_MODE)
                
            elif mode == PPU.H_BLANK_MODE:

                if self.clk >= PPU.H_BLANK_TIME:
                    self.clk -= PPU.H_BLANK_TIME
                    y = self.emu.read(LY_ADDR) + 1
                    self.updateLY(y)
                    if y == 0x90: # 144
                        self.updateMode(PPU.V_BLANK_MODE)
                        self.render()
                        self.emu.z80.setInterrupt(IF_VBLANK)
                        # whole frame ready, prepare to show a new screen and handle inputs
                        self.emu.frames += 1
                        self.updateLCD()
                    else:
                        self.updateMode(PPU.OAM_READ_MODE)
                    
            elif mode == PPU.V_BLANK_MODE:

                if self.clk >= PPU.V_BLANK_TIME:
                    self.clk -= PPU.V_BLANK_TIME
                    y = self.emu.read(LY_ADDR) + 1
                    if y == 0x9A: # 154
                        self.updateMode(PPU.OAM_READ_MODE)
                        self.updateLY(0)
                    else:
                        self.updateLY(y)

    def updateLY(self, y: int) -> None:
        self.emu.write(LY_ADDR, y)
        lyc = self.emu.read(LYC_ADDR)
        stat = self.emu.read(STAT_ADDR)
        if y == lyc:
            self.emu.write(STAT_ADDR, setBit(stat, STAT_LYC_STAT, 1))
            if getBit(self.emu.read(STAT_ADDR), STAT_INTR_LYC):
                self.emu.z80.setInterrupt(IF_STAT)
        else:
            self.emu.write(STAT_ADDR, setBit(stat, STAT_LYC_STAT, 0))
    
    def updateMode(self, mode: int) -> None:
        stat = setBit(self.emu.read(STAT_ADDR), STAT_LCD_MODE, mode, bit2=True)
        self.emu.write(STAT_ADDR, stat)

        if getBit(stat, mode + 3) and mode != 3:
            self.emu.z80.setInterrupt(IF_STAT)
    
    def updateLCD(self) -> None:
        # *********
        # * 1 * 2 *
        # *********
        # * 3 * 4 *
        # *********
        # part 1
        self.LCD.blit(
            self.buffer,
            (0, 0),
            pygame.Rect(
                self.scx * RESIZE,
                self.scy * RESIZE,
                min(256 - self.scx, COLS) * RESIZE,
                min(256 - self.scy, ROWS) * RESIZE
            )
        )
        # part 2
        if self.scx > 96:
            self.LCD.blit(
                self.buffer,
                ((256 - self.scx) * RESIZE, 0),
                pygame.Rect(
                    0,
                    self.scy * RESIZE,
                    (self.scx - 96) * RESIZE,
                    min(256 - self.scy, ROWS) * RESIZE
                )
            )
        # part 3
        if self.scy > 112:
            self.LCD.blit(
                self.buffer,
                (0, (256 - self.scy) * RESIZE),
                pygame.Rect(
                    self.scx * RESIZE,
                    0,
                    min(256 - self.scx, COLS) * RESIZE,
                    (self.scy - 112) * RESIZE
                )
            )
        # part 4
        if self.scx > 96 and self.scy > 112:
            self.LCD.blit(
                self.buffer,
                ((256 - self.scx) * RESIZE, (256 - self.scy) * RESIZE),
                pygame.Rect(
                    0,
                    0,
                    (self.scx - 96) * RESIZE,
                    (self.scy - 112) * RESIZE
                )
            )
        pygame.display.flip()

    def render(self) -> None:
        self.scx = self.emu.read(SCX_ADDR)
        self.scy = self.emu.read(SCY_ADDR)
        pixels = pygame.PixelArray(self.buffer)
        self.renderBackground(pixels)
        self.renderWindow(pixels)
        self.renderSprites(pixels)
        del pixels
    
    def renderBackground(self, pixels: pygame.PixelArray) -> None:
        lcdc = self.emu.read(LCDC_ADDR)
        if not getBit(lcdc, LCDC_BG_EN): return

        mapAddr = 0x9C00 if getBit(lcdc, LCDC_BG_MAP) else 0x9800

        for offset in range(0x400):
            tileIdx = self.emu.read(mapAddr + offset)
            if getBit(lcdc, LCDC_TILE_SEL):
                tileAddr = 0x8000
            else:
                tileAddr = 0x8800
                tileIdx = (tileIdx - 0x100) & 0xFF
            
            if self.cache[offset] == tileIdx:
                continue
            else:
                self.cache[offset] = tileIdx

            tile = Tile(self.emu, tileAddr + tileIdx * 0x10)
            for dy in range(tile.ROWS):
                for dx in range(tile.COLS):
                    PPU.fill(offset % 32 * 8 + dx, offset // 32 * 8 + dy, tile.pixels[dy][dx], pixels)
            del tile
    
    def renderWindow(self, pixels: pygame.PixelArray) -> None:
        lcdc = self.emu.read(LCDC_ADDR)
        if not getBit(lcdc, LCDC_WIN_EN): return

        mapAddr = 0x9C00 if getBit(lcdc, LCDC_WIN_MAP) else 0x9800
        wx, wy = self.emu.read(WX_ADDR) - 7, self.emu.read(WY_ADDR)

        for offset in range(0x400):
            tileIdx = self.emu.read(mapAddr + offset)
            if getBit(lcdc, LCDC_TILE_SEL):
                tileAddr = 0x8000
            else:
                tileAddr = 0x8800
                tileIdx -= 0x100
            
            tile = Tile(self.emu, tileAddr + tileIdx * 16)
            for dy in range(tile.ROWS):
                y = wy + offset // 32 * 8 + dy
                if not (0 <= y < ROWS): continue
                for dx in range(tile.COLS):
                    x = wx + offset % 32 * 8 + dx
                    if not (0 <= x < COLS): continue
                    PPU.fill(x, y, tile.pixels[dy][dx], pixels)
            del tile
    
    def renderSprites(self, pixels: pygame.PixelArray) -> None:
        lcdc = self.emu.read(LCDC_ADDR)
        if not getBit(lcdc, LCDC_OBJ_EN): return

        Sprite = SpriteTile16 if getBit(lcdc, LCDC_OBJ_SIZE) else SpriteTile8
        
        for addr in range(0xFE00, 0xFEA0, 4):
            tile = Sprite(self.emu, addr)
            for dy in range(tile.ROWS):
                if not (0 <= tile.y + dy < ROWS): continue
                for dx in range(tile.COLS):
                    if not (0 <= tile.x + dx < COLS): continue

                    x, y = self.scx + tile.x + dx, self.scy + tile.y + dy
                    if tile.priority or pixels[x * RESIZE, y * RESIZE] == getColor(0, PPU.NOSTALGIC):
                        if tile.pixels[dy][dx] < 0: continue
                        PPU.fill(x, y, tile.pixels[dy][dx], pixels)
            del tile
    
    def handleEvents(self) -> None:

        def quit() -> None:
            pygame.display.quit()
            pygame.quit()
            sys.exit()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()
            elif event.type == pygame.KEYDOWN:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_RIGHT]:
                    self.dir &= 0xE
                    print('\t→ pressed')
                elif keys[pygame.K_LEFT]:
                    self.dir &= 0xD
                    print('\t← pressed')
                elif keys[pygame.K_UP]:
                    self.dir &= 0xB
                    print('\t↑ pressed')
                elif keys[pygame.K_DOWN]:
                    self.dir &= 0x7
                    print('\t↓ pressed')
                elif keys[pygame.K_z]:
                    # button A
                    self.std &= 0xE
                    print('\tA pressed')
                elif keys[pygame.K_x]:
                    # button B
                    self.std &= 0xD
                    print('\tB pressed')
                elif keys[pygame.K_BACKSPACE]:
                    # button select
                    self.std &= 0xB
                    print('\tselect pressed')
                elif keys[pygame.K_RETURN]:
                    # button start
                    self.std &= 0x7
                    print('\tstart pressed')
                elif keys[pygame.K_h]:
                    # help
                    print(INSTRUCTION)
                elif keys[pygame.K_q]:
                    quit()
                elif keys[pygame.K_p]:
                    # pause
                    self.emu.paused = not self.emu.paused
                elif keys[pygame.K_s]:
                    # screenshot
                    if not os.path.exists(SCREENSHOT_PATH):
                        os.mkdir(SCREENSHOT_PATH)
                    pygame.image.save(self.LCD, f'{SCREENSHOT_PATH}/screenshot_{toHex(int(time.time()))}.jpg')
                elif keys[pygame.K_c]:
                    # clear console output
                    os.system('clear')
                elif keys[pygame.K_r]:
                    # print registers
                    self.emu.printReg()
                elif keys[pygame.K_m]:
                    # print memory
                    if keys[pygame.K_1]:
                        self.emu.printMem('Tile Field 1:', 0x8000, 0x9000, 0x10)
                    elif keys[pygame.K_2]:
                        self.emu.printMem('Tile Field 2:', 0x8800, 0x9800, 0x10)
                    elif keys[pygame.K_3]:
                        self.emu.printMem('Map Field 1:', 0x9800, 0x9C00, 0x20)
                    elif keys[pygame.K_4]:
                        self.emu.printMem('Map Field 2:', 0x9C00, 0xA000, 0x20)
                    elif keys[pygame.K_5]:
                        self.emu.printMem('OAM:', 0xFE00, 0xFEA0, 0x04)
                    elif keys[pygame.K_6]:
                        self.emu.printMem('FF registers', 0xFF00, 0x10000, 0x10)
            elif event.type == pygame.KEYUP:
                released = event.key
                if released == pygame.K_RIGHT:
                    self.dir |= 0x1
                    print('\t→ released')
                elif released == pygame.K_LEFT:
                    self.dir |= 0x2
                    print('\t← released')
                elif released == pygame.K_UP:
                    self.dir |= 0x4
                    print('\t↑ released')
                elif released == pygame.K_DOWN:
                    self.dir |= 0x8
                    print('\t↓ released')
                elif released == pygame.K_z:
                    # button A
                    self.std |= 0x1
                    print('\tA released')
                elif released == pygame.K_x:
                    # button B
                    self.std |= 0x2
                    print('\tB released')
                elif released == pygame.K_BACKSPACE:
                    # button select
                    self.std |= 0x4
                    print('\tselect released')
                elif released == pygame.K_RETURN:
                    # button start
                    self.std |= 0x8
                    print('\tstart released')
    
    def pullButton(self, byte: int) -> int:
        if byte == 0x10:
            return self.std & 0xF
        elif byte == 0x20:
            return self.dir & 0xF
        else:
            return 0
    
    @staticmethod
    def fill(x: int, y: int, colorCode: int, pixels: pygame.PixelArray) -> None:
        for dy in range(RESIZE):
            for dx in range(RESIZE):
                pixels[x * RESIZE + dx, y * RESIZE + dy] = getColor(colorCode, PPU.NOSTALGIC)

    @staticmethod
    def delay(ms: int) -> None:
        pygame.time.delay(ms)
