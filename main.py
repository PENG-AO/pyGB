from emulator import Emulator

ROM = './romfile.gb'
emu = Emulator(ROM, skipBios=True, nostalgic=True)
emu.run()
