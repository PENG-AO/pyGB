from emulator import Emulator

# ROM = './test_rom/cpu_instr/08.gb'
ROM = './test_rom/games/Tetris.gb'
emu = Emulator(ROM, skipBios=False, nostalgic=False)
try:
    emu.run()
except Exception as e:
    raise e
