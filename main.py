from emulator import Emulator

ROM = './test_rom/cpu_instr/11.gb'
# ROM = './test_rom/games/opus5.gb'
emu = Emulator(ROM, skipBios=True, nostalgic=True)
'''
# add a sprite info
emu.write(0xFE00, 0x54)
emu.write(0xFE01, 0x54)
emu.write(0xFE02, 0x02)
emu.write(0xFE03, 0x00)
'''
emu.run()
