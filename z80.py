# z80 cpu
from utils import toHex
# register F
FLAG_C, FLAG_H, FLAG_N, FLAG_Z = 4, 5, 6, 7
# addresses of registers
IF_ADDR = 0xFF0F
IE_ADDR = 0xFFFF
# interruptions
IF_VBLANK, IF_STAT, IF_TIMER, IF_SERIAL, IF_JOYPAD = 0, 1, 2, 3, 4

class Z80(object):

    __slots__ = (
        'A', 'B', 'C', 'D', 'E', 'F', 'H', 'L',
        'PC', 'SP', 'emu',
        'interruptable', 'halted',
        'opcode', 'opname', 'args', 'OP_MAP'
    )

    def __init__(self, emu) -> None:
        # 15...8 7...0
        # |  A  |  F  |
        # |  B  |  C  |
        # |  D  |  E  |
        # |  H  |  L  |
        # |    SP     |
        # |    PC     |
        # F : 7 6 5 4 3 2 1 0
        #     Z N H C 0 0 0 0
        # 8-bit registers
        self.A = 0x00
        self.B = 0x00
        self.C = 0x00
        self.D = 0x00
        self.E = 0x00
        self.F = 0x00
        self.H = 0x00
        self.L = 0x00
        # 16-bit registers
        self.PC = 0x0000
        self.SP = 0x0000
        # reference of emulator
        self.emu = emu
        # interrupt
        self.interruptable = False
        self.halted = False
        # info of opcode
        self.opcode = 0x00
        self.opname = 'NOP'
        self.args = [0x00, 0x00]
        self.OP_MAP = [
            # 0x
            (NOP_00   , 1, 'NOP'        ),(LD_01    , 3, 'LD BC,d16'  ),(LD_02    , 1, 'LD (BC),A'  ),(INC_03   , 1, 'INC BC'     ),
            (INC_04   , 1, 'INC B'      ),(DEC_05   , 1, 'DEC B'      ),(LD_06    , 2, 'LD B,d8'    ),(RLCA_07  , 1, 'RLCA'       ),
            (LD_08    , 3, 'LD (a16),SP'),(ADD_09   , 1, 'ADD HL,BC'  ),(LD_0A    , 1, 'LD A,(BC)'  ),(DEC_0B   , 1, 'DEC BC'     ),
            (INC_0C   , 1, 'INC C'      ),(DEC_0D   , 1, 'DEC C'      ),(LD_0E    , 2, 'LD C,d8'    ),(RRCA_0F  , 1, 'RRCA'       ),
            # 1x
            (STOP_10  , 2, 'STOP 0'     ),(LD_11    , 3, 'LD DE,d16'  ),(LD_12    , 1, 'LD (DE),A'  ),(INC_13   , 1, 'INC DE'     ),
            (INC_14   , 1, 'INC D'      ),(DEC_15   , 1, 'DEC D'      ),(LD_16    , 2, 'LD D,d8'    ),(RLA_17   , 1, 'RLA'        ),
            (JR_18    , 2, 'JR r8'      ),(ADD_19   , 1, 'ADD HL,DE'  ),(LD_1A    , 1, 'LD A,(DE)'  ),(DEC_1B   , 1, 'DEC DE'     ),
            (INC_1C   , 1, 'INC E'      ),(DEC_1D   , 1, 'DEC E'      ),(LD_1E    , 2, 'LD E,d8'    ),(RRA_1F   , 1, 'RRA'        ),
            # 2x
            (JR_20    , 2, 'JR NZ,r8'   ),(LD_21    , 3, 'LD HL,d16'  ),(LD_22    , 1, 'LD (HL+),A' ),(INC_23   , 1, 'INC HL'     ),
            (INC_24   , 1, 'INC H'      ),(DEC_25   , 1, 'DEC H'      ),(LD_26    , 2, 'LD H,d8'    ),(DAA_27   , 1, 'DAA'        ),
            (JR_28    , 2, 'JR Z,r8'    ),(ADD_29   , 1, 'ADD HL,HL'  ),(LD_2A    , 1, 'LD A,(HL+)' ),(DEC_2B   , 1, 'DEC HL'     ),
            (INC_2C   , 1, 'INC L'      ),(DEC_2D   , 1, 'DEC L'      ),(LD_2E    , 2, 'LD L,d8'    ),(CPL_2F   , 1, 'CPL'        ),
            # 3x
            (JR_30    , 2, 'JR NC,r8'   ),(LD_31    , 3, 'LD SP,d16'  ),(LD_32    , 1, 'LD (HL-),A' ),(INC_33   , 1, 'INC SP'     ),
            (INC_34   , 1, 'INC (HL)'   ),(DEC_35   , 1, 'DEC (HL)'   ),(LD_36    , 2, 'LD (HL),d8' ),(SCF_37   , 1, 'SCF'        ),
            (JR_38    , 2, 'JR C,r8'    ),(ADD_39   , 1, 'ADD HL,SP'  ),(LD_3A    , 1, 'LD A,(HL-)' ),(DEC_3B   , 1, 'DEC SP'     ),
            (INC_3C   , 1, 'INC A'      ),(DEC_3D   , 1, 'DEC A'      ),(LD_3E    , 2, 'LD A,d8'    ),(CCF_3F   , 1, 'CCF'        ),
            # 4x
            (LD_40    , 1, 'LD B,B'     ),(LD_41    , 1, 'LD B,C'     ),(LD_42    , 1, 'LD B,D'     ),(LD_43    , 1, 'LD B,E'     ),
            (LD_44    , 1, 'LD B,H'     ),(LD_45    , 1, 'LD B,L'     ),(LD_46    , 1, 'LD B,(HL)'  ),(LD_47    , 1, 'LD B,A'     ),
            (LD_48    , 1, 'LD C,B'     ),(LD_49    , 1, 'LD C,C'     ),(LD_4A    , 1, 'LD C,D'     ),(LD_4B    , 1, 'LD C,E'     ),
            (LD_4C    , 1, 'LD C,H'     ),(LD_4D    , 1, 'LD C,L'     ),(LD_4E    , 1, 'LD C,(HL)'  ),(LD_4F    , 1, 'LD C,A'     ),
            # 5x
            (LD_50    , 1, 'LD D,B'     ),(LD_51    , 1, 'LD D,C'     ),(LD_52    , 1, 'LD D,D'     ),(LD_53    , 1, 'LD D,E'     ),
            (LD_54    , 1, 'LD D,H'     ),(LD_55    , 1, 'LD D,L'     ),(LD_56    , 1, 'LD D,(HL)'  ),(LD_57    , 1, 'LD D,A'     ),
            (LD_58    , 1, 'LD E,B'     ),(LD_59    , 1, 'LD E,C'     ),(LD_5A    , 1, 'LD E,D'     ),(LD_5B    , 1, 'LD E,E'     ),
            (LD_5C    , 1, 'LD E,H'     ),(LD_5D    , 1, 'LD E,L'     ),(LD_5E    , 1, 'LD E,(HL)'  ),(LD_5F    , 1, 'LD E,A'     ),
            # 6x
            (LD_60    , 1, 'LD H,B'     ),(LD_61    , 1, 'LD H,C'     ),(LD_62    , 1, 'LD H,D'     ),(LD_63    , 1, 'LD H,E'     ),
            (LD_64    , 1, 'LD H,H'     ),(LD_65    , 1, 'LD H,L'     ),(LD_66    , 1, 'LD H,(HL)'  ),(LD_67    , 1, 'LD H,A'     ),
            (LD_68    , 1, 'LD L,B'     ),(LD_69    , 1, 'LD L,C'     ),(LD_6A    , 1, 'LD L,D'     ),(LD_6B    , 1, 'LD L,E'     ),
            (LD_6C    , 1, 'LD L,H'     ),(LD_6D    , 1, 'LD L,L'     ),(LD_6E    , 1, 'LD L,(HL)'  ),(LD_6F    , 1, 'LD L,A'     ),
            # 7x
            (LD_70    , 1, 'LD (HL),B'  ),(LD_71    , 1, 'LD (HL),C'  ),(LD_72    , 1, 'LD (HL),D'  ),(LD_73    , 1, 'LD (HL),E'  ),
            (LD_74    , 1, 'LD (HL),H'  ),(LD_75    , 1, 'LD (HL),L'  ),(HALT_76  , 1, 'HALT'       ),(LD_77    , 1, 'LD (HL),A'  ),
            (LD_78    , 1, 'LD A,B'     ),(LD_79    , 1, 'LD A,C'     ),(LD_7A    , 1, 'LD A,D'     ),(LD_7B    , 1, 'LD A,E'     ),
            (LD_7C    , 1, 'LD A,H'     ),(LD_7D    , 1, 'LD A,L'     ),(LD_7E    , 1, 'LD A,(HL)'  ),(LD_7F    , 1, 'LD A,A'     ),
            # 8x
            (ADD_80   , 1, 'ADD A,B'    ),(ADD_81   , 1, 'ADD A,C'    ),(ADD_82   , 1, 'ADD A,D'    ),(ADD_83   , 1, 'ADD A,E'    ),
            (ADD_84   , 1, 'ADD A,H'    ),(ADD_85   , 1, 'ADD A,L'    ),(ADD_86   , 1, 'ADD A,(HL)' ),(ADD_87   , 1, 'ADD A,A'    ),
            (ADC_88   , 1, 'ADC A,B'    ),(ADC_89   , 1, 'ADC A,C'    ),(ADC_8A   , 1, 'ADC A,D'    ),(ADC_8B   , 1, 'ADC A,E'    ),
            (ADC_8C   , 1, 'ADC A,H'    ),(ADC_8D   , 1, 'ADC A,L'    ),(ADC_8E   , 1, 'ADC A,(HL)' ),(ADC_8F   , 1, 'ADC A,A'    ),
            # 9x
            (SUB_90   , 1, 'SUB B'      ),(SUB_91   , 1, 'SUB C'      ),(SUB_92   , 1, 'SUB D'      ),(SUB_93   , 1, 'SUB E'      ),
            (SUB_94   , 1, 'SUB H'      ),(SUB_95   , 1, 'SUB L'      ),(SUB_96   , 1, 'SUB (HL)'   ),(SUB_97   , 1, 'SUB A'      ),
            (SBC_98   , 1, 'SBC A,B'    ),(SBC_99   , 1, 'SBC A,C'    ),(SBC_9A   , 1, 'SBC A,D'    ),(SBC_9B   , 1, 'SBC A,E'    ),
            (SBC_9C   , 1, 'SBC A,H'    ),(SBC_9D   , 1, 'SBC A,L'    ),(SBC_9E   , 1, 'SBC A,(HL)' ),(SBC_9F   , 1, 'SBC A,A'    ),
            # Ax
            (AND_A0   , 1, 'AND B'      ),(AND_A1   , 1, 'AND C'      ),(AND_A2   , 1, 'AND D'      ),(AND_A3   , 1, 'AND E'      ),
            (AND_A4   , 1, 'AND H'      ),(AND_A5   , 1, 'AND L'      ),(AND_A6   , 1, 'AND (HL)'   ),(AND_A7   , 1, 'AND A'      ),
            (XOR_A8   , 1, 'XOR B'      ),(XOR_A9   , 1, 'XOR C'      ),(XOR_AA   , 1, 'XOR D'      ),(XOR_AB   , 1, 'XOR E'      ),
            (XOR_AC   , 1, 'XOR H'      ),(XOR_AD   , 1, 'XOR L'      ),(XOR_AE   , 1, 'XOR (HL)'   ),(XOR_AF   , 1, 'XOR A'      ),
            # Bx
            (OR_B0    , 1, 'OR B'       ),(OR_B1    , 1, 'OR C'       ),(OR_B2    , 1, 'OR D'       ),(OR_B3    , 1, 'OR E'       ),
            (OR_B4    , 1, 'OR H'       ),(OR_B5    , 1, 'OR L'       ),(OR_B6    , 1, 'OR (HL)'    ),(OR_B7    , 1, 'OR A'       ),
            (CP_B8    , 1, 'CP B'       ),(CP_B9    , 1, 'CP C'       ),(CP_BA    , 1, 'CP D'       ),(CP_BB    , 1, 'CP E'       ),
            (CP_BC    , 1, 'CP H'       ),(CP_BD    , 1, 'CP L'       ),(CP_BE    , 1, 'CP (HL)'    ),(CP_BF    , 1, 'CP A'       ),
            # Cx
            (RET_C0   , 1, 'RET NZ'     ),(POP_C1   , 1, 'POP BC'     ),(JP_C2    , 3, 'JP NZ,a16'  ),(JP_C3    , 3, 'JP a16'     ),
            (CALL_C4  , 3, 'CALL NZ,a16'),(PUSH_C5  , 1, 'PUSH BC'    ),(ADD_C6   , 2, 'ADD A,d8'   ),(RST_C7   , 1, 'RST 00H'    ),
            (RET_C8   , 1, 'RET Z'      ),(RET_C9   , 1, 'RET'        ),(JP_CA    , 3, 'JP Z,a16'   ),(PREFIX_CB, 1, 'PREFIX CB'  ),
            (CALL_CC  , 3, 'CALL Z,a16' ),(CALL_CD  , 3, 'CALL a16'   ),(ADC_CE   , 2, 'ADC A,d8'   ),(RST_CF   , 1, 'RST 08H'    ),
            # Dx
            (RET_D0   , 1, 'RET NC'     ),(POP_D1   , 1, 'POP DE'     ),(JP_D2    , 3, 'JP NC,a16'  ),(NULL     , 0, ''           ),
            (CALL_D4  , 3, 'CALL NC,a16'),(PUSH_D5  , 1, 'PUSH DE'    ),(SUB_D6   , 2, 'SUB d8'     ),(RST_D7   , 1, 'RST 10H'    ),
            (RET_D8   , 1, 'RET C'      ),(RETI_D9  , 1, 'RETI'       ),(JP_DA    , 3, 'JP C,a16'   ),(NULL     , 0, ''           ),
            (CALL_DC  , 3, 'CALL C,a16' ),(NULL     , 0, ''           ),(SBC_DE   , 2, 'SBC A,d8'   ),(RST_DF   , 1, 'RST 18H'    ),
            # Ex
            (LDH_E0   , 2, 'LDH (a8),A' ),(POP_E1   , 1, 'POP HL'     ),(LD_E2    , 1, 'LD (C),A'   ),(NULL     , 0, ''           ),
            (NULL     , 0, ''           ),(PUSH_E5  , 1, 'PUSH HL'    ),(AND_E6   , 2, 'AND d8'     ),(RST_E7   , 1, 'RST 20H'    ),
            (ADD_E8   , 2, 'ADD SP,r8'  ),(JP_E9    , 1, 'JP (HL)'    ),(LD_EA    , 3, 'LD (a16),A' ),(NULL     , 0, ''           ),
            (NULL     , 0, ''           ),(NULL     , 0, ''           ),(XOR_EE   , 2, 'XOR d8'     ),(RST_EF   , 1, 'RST 28H'    ),
            # Fx
            (LDH_F0   , 2, 'LDH A,(a8)' ),(POP_F1   , 1, 'POP AF'     ),(LD_F2    , 1, 'LD A,(C)'   ),(DI_F3    , 1, 'DI'         ),
            (NULL     , 0, ''           ),(PUSH_F5  , 1, 'PUSH AF'    ),(OR_F6    , 2, 'OR d8'      ),(RST_F7   , 1, 'RST 30H'    ),
            (LD_F8    , 2, 'LD HL,SP+r8'),(LD_F9    , 1, 'LD SP,HL'   ),(LD_FA    , 3, 'LD A,(a16)' ),(EI_FB    , 1, 'EI'         ),
            (NULL     , 0, ''           ),(NULL     , 0, ''           ),(CP_FE    , 2, 'CP d8'      ),(RST_FF   , 1, 'RST 38H'    ),
            # 10x
            (RLC_100  , 2, 'RLC B'      ),(RLC_101  , 2, 'RLC C'      ),(RLC_102  , 2, 'RLC D'      ),(RLC_103  , 2, 'RLC E'      ),
            (RLC_104  , 2, 'RLC H'      ),(RLC_105  , 2, 'RLC L'      ),(RLC_106  , 2, 'RLC (HL)'   ),(RLC_107  , 2, 'RLC A'      ),
            (RRC_108  , 2, 'RRC B'      ),(RRC_109  , 2, 'RRC C'      ),(RRC_10A  , 2, 'RRC D'      ),(RRC_10B  , 2, 'RRC E'      ),
            (RRC_10C  , 2, 'RRC H'      ),(RRC_10D  , 2, 'RRC L'      ),(RRC_10E  , 2, 'RRC (HL)'   ),(RRC_10F  , 2, 'RRC A'      ),
            # 11x
            (RL_110   , 2, 'RL B'       ),(RL_111   , 2, 'RL C'       ),(RL_112   , 2, 'RL D'       ),(RL_113   , 2, 'RL E'       ),
            (RL_114   , 2, 'RL H'       ),(RL_115   , 2, 'RL L'       ),(RL_116   , 2, 'RL (HL)'    ),(RL_117   , 2, 'RL A'       ),
            (RR_118   , 2, 'RR B'       ),(RR_119   , 2, 'RR C'       ),(RR_11A   , 2, 'RR D'       ),(RR_11B   , 2, 'RR E'       ),
            (RR_11C   , 2, 'RR H'       ),(RR_11D   , 2, 'RR L'       ),(RR_11E   , 2, 'RR (HL)'    ),(RR_11F   , 2, 'RR A'       ),
            # 12x
            (SLA_120  , 2, 'SLA B'      ),(SLA_121  , 2, 'SLA C'      ),(SLA_122  , 2, 'SLA D'      ),(SLA_123  , 2, 'SLA E'      ),
            (SLA_124  , 2, 'SLA H'      ),(SLA_125  , 2, 'SLA L'      ),(SLA_126  , 2, 'SLA (HL)'   ),(SLA_127  , 2, 'SLA A'      ),
            (SRA_128  , 2, 'SRA B'      ),(SRA_129  , 2, 'SRA C'      ),(SRA_12A  , 2, 'SRA D'      ),(SRA_12B  , 2, 'SRA E'      ),
            (SRA_12C  , 2, 'SRA H'      ),(SRA_12D  , 2, 'SRA L'      ),(SRA_12E  , 2, 'SRA (HL)'   ),(SRA_12F  , 2, 'SRA A'      ),
            # 13x
            (SWAP_130 , 2, 'SWAP B'     ),(SWAP_131 , 2, 'SWAP C'     ),(SWAP_132 , 2, 'SWAP D'     ),(SWAP_133 , 2, 'SWAP E'     ),
            (SWAP_134 , 2, 'SWAP H'     ),(SWAP_135 , 2, 'SWAP L'     ),(SWAP_136 , 2, 'SWAP (HL)'  ),(SWAP_137 , 2, 'SWAP A'     ),
            (SRL_138  , 2, 'SRL B'      ),(SRL_139  , 2, 'SRL C'      ),(SRL_13A  , 2, 'SRL D'      ),(SRL_13B  , 2, 'SRL E'      ),
            (SRL_13C  , 2, 'SRL H'      ),(SRL_13D  , 2, 'SRL L'      ),(SRL_13E  , 2, 'SRL (HL)'   ),(SRL_13F  , 2, 'SRL A'      ),
            # 14x
            (BIT_140  , 2, 'BIT 0,B'    ),(BIT_141  , 2, 'BIT 0,C'    ),(BIT_142  , 2, 'BIT 0,D'    ),(BIT_143  , 2, 'BIT 0,E'    ),
            (BIT_144  , 2, 'BIT 0,H'    ),(BIT_145  , 2, 'BIT 0,L'    ),(BIT_146  , 2, 'BIT 0,(HL)' ),(BIT_147  , 2, 'BIT 0,A'    ),
            (BIT_148  , 2, 'BIT 1,B'    ),(BIT_149  , 2, 'BIT 1,C'    ),(BIT_14A  , 2, 'BIT 1,D'    ),(BIT_14B  , 2, 'BIT 1,E'    ),
            (BIT_14C  , 2, 'BIT 1,H'    ),(BIT_14D  , 2, 'BIT 1,L'    ),(BIT_14E  , 2, 'BIT 1,(HL)' ),(BIT_14F  , 2, 'BIT 1,A'    ),
            # 15x
            (BIT_150  , 2, 'BIT 2,B'    ),(BIT_151  , 2, 'BIT 2,C'    ),(BIT_152  , 2, 'BIT 2,D'    ),(BIT_153  , 2, 'BIT 2,E'    ),
            (BIT_154  , 2, 'BIT 2,H'    ),(BIT_155  , 2, 'BIT 2,L'    ),(BIT_156  , 2, 'BIT 2,(HL)' ),(BIT_157  , 2, 'BIT 2,A'    ),
            (BIT_158  , 2, 'BIT 3,B'    ),(BIT_159  , 2, 'BIT 3,C'    ),(BIT_15A  , 2, 'BIT 3,D'    ),(BIT_15B  , 2, 'BIT 3,E'    ),
            (BIT_15C  , 2, 'BIT 3,H'    ),(BIT_15D  , 2, 'BIT 3,L'    ),(BIT_15E  , 2, 'BIT 3,(HL)' ),(BIT_15F  , 2, 'BIT 3,A'    ),
            # 16x
            (BIT_160  , 2, 'BIT 4,B'    ),(BIT_161  , 2, 'BIT 4,C'    ),(BIT_162  , 2, 'BIT 4,D'    ),(BIT_163  , 2, 'BIT 4,E'    ),
            (BIT_164  , 2, 'BIT 4,H'    ),(BIT_165  , 2, 'BIT 4,L'    ),(BIT_166  , 2, 'BIT 4,(HL)' ),(BIT_167  , 2, 'BIT 4,A'    ),
            (BIT_168  , 2, 'BIT 5,B'    ),(BIT_169  , 2, 'BIT 5,C'    ),(BIT_16A  , 2, 'BIT 5,D'    ),(BIT_16B  , 2, 'BIT 5,E'    ),
            (BIT_16C  , 2, 'BIT 5,H'    ),(BIT_16D  , 2, 'BIT 5,L'    ),(BIT_16E  , 2, 'BIT 5,(HL)' ),(BIT_16F  , 2, 'BIT 5,A'    ),
            # 17x
            (BIT_170  , 2, 'BIT 6,B'    ),(BIT_171  , 2, 'BIT 6,C'    ),(BIT_172  , 2, 'BIT 6,D'    ),(BIT_173  , 2, 'BIT 6,E'    ),
            (BIT_174  , 2, 'BIT 6,H'    ),(BIT_175  , 2, 'BIT 6,L'    ),(BIT_176  , 2, 'BIT 6,(HL)' ),(BIT_177  , 2, 'BIT 6,A'    ),
            (BIT_178  , 2, 'BIT 7,B'    ),(BIT_179  , 2, 'BIT 7,C'    ),(BIT_17A  , 2, 'BIT 7,D'    ),(BIT_17B  , 2, 'BIT 7,E'    ),
            (BIT_17C  , 2, 'BIT 7,H'    ),(BIT_17D  , 2, 'BIT 7,L'    ),(BIT_17E  , 2, 'BIT 7,(HL)' ),(BIT_17F  , 2, 'BIT 7,A'    ),
            # 18x
            (RES_180  , 2, 'RES 0,B'    ),(RES_181  , 2, 'RES 0,C'    ),(RES_182  , 2, 'RES 0,D'    ),(RES_183  , 2, 'RES 0,E'    ),
            (RES_184  , 2, 'RES 0,H'    ),(RES_185  , 2, 'RES 0,L'    ),(RES_186  , 2, 'RES 0,(HL)' ),(RES_187  , 2, 'RES 0,A'    ),
            (RES_188  , 2, 'RES 1,B'    ),(RES_189  , 2, 'RES 1,C'    ),(RES_18A  , 2, 'RES 1,D'    ),(RES_18B  , 2, 'RES 1,E'    ),
            (RES_18C  , 2, 'RES 1,H'    ),(RES_18D  , 2, 'RES 1,L'    ),(RES_18E  , 2, 'RES 1,(HL)' ),(RES_18F  , 2, 'RES 1,A'    ),
            # 19x
            (RES_190  , 2, 'RES 2,B'    ),(RES_191  , 2, 'RES 2,C'    ),(RES_192  , 2, 'RES 2,D'    ),(RES_193  , 2, 'RES 2,E'    ),
            (RES_194  , 2, 'RES 2,H'    ),(RES_195  , 2, 'RES 2,L'    ),(RES_196  , 2, 'RES 2,(HL)' ),(RES_197  , 2, 'RES 2,A'    ),
            (RES_198  , 2, 'RES 3,B'    ),(RES_199  , 2, 'RES 3,C'    ),(RES_19A  , 2, 'RES 3,D'    ),(RES_19B  , 2, 'RES 3,E'    ),
            (RES_19C  , 2, 'RES 3,H'    ),(RES_19D  , 2, 'RES 3,L'    ),(RES_19E  , 2, 'RES 3,(HL)' ),(RES_19F  , 2, 'RES 3,A'    ),
            # 1Ax
            (RES_1A0  , 2, 'RES 4,B'    ),(RES_1A1  , 2, 'RES 4,C'    ),(RES_1A2  , 2, 'RES 4,D'    ),(RES_1A3  , 2, 'RES 4,E'    ),
            (RES_1A4  , 2, 'RES 4,H'    ),(RES_1A5  , 2, 'RES 4,L'    ),(RES_1A6  , 2, 'RES 4,(HL)' ),(RES_1A7  , 2, 'RES 4,A'    ),
            (RES_1A8  , 2, 'RES 5,B'    ),(RES_1A9  , 2, 'RES 5,C'    ),(RES_1AA  , 2, 'RES 5,D'    ),(RES_1AB  , 2, 'RES 5,E'    ),
            (RES_1AC  , 2, 'RES 5,H'    ),(RES_1AD  , 2, 'RES 5,L'    ),(RES_1AE  , 2, 'RES 5,(HL)' ),(RES_1AF  , 2, 'RES 5,A'    ),
            # 1Bx
            (RES_1B0  , 2, 'RES 6,B'    ),(RES_1B1  , 2, 'RES 6,C'    ),(RES_1B2  , 2, 'RES 6,D'    ),(RES_1B3  , 2, 'RES 6,E'    ),
            (RES_1B4  , 2, 'RES 6,H'    ),(RES_1B5  , 2, 'RES 6,L'    ),(RES_1B6  , 2, 'RES 6,(HL)' ),(RES_1B7  , 2, 'RES 6,A'    ),
            (RES_1B8  , 2, 'RES 7,B'    ),(RES_1B9  , 2, 'RES 7,C'    ),(RES_1BA  , 2, 'RES 7,D'    ),(RES_1BB  , 2, 'RES 7,E'    ),
            (RES_1BC  , 2, 'RES 7,H'    ),(RES_1BD  , 2, 'RES 7,L'    ),(RES_1BE  , 2, 'RES 7,(HL)' ),(RES_1BF  , 2, 'RES 7,A'    ),
            # 1Cx
            (SET_1C0  , 2, 'SET 0,B'    ),(SET_1C1  , 2, 'SET 0,C'    ),(SET_1C2  , 2, 'SET 0,D'    ),(SET_1C3  , 2, 'SET 0,E'    ),
            (SET_1C4  , 2, 'SET 0,H'    ),(SET_1C5  , 2, 'SET 0,L'    ),(SET_1C6  , 2, 'SET 0,(HL)' ),(SET_1C7  , 2, 'SET 0,A'    ),
            (SET_1C8  , 2, 'SET 1,B'    ),(SET_1C9  , 2, 'SET 1,C'    ),(SET_1CA  , 2, 'SET 1,D'    ),(SET_1CB  , 2, 'SET 1,E'    ),
            (SET_1CC  , 2, 'SET 1,H'    ),(SET_1CD  , 2, 'SET 1,L'    ),(SET_1CE  , 2, 'SET 1,(HL)' ),(SET_1CF  , 2, 'SET 1,A'    ),
            # 1Dx
            (SET_1D0  , 2, 'SET 2,B'    ),(SET_1D1  , 2, 'SET 2,C'    ),(SET_1D2  , 2, 'SET 2,D'    ),(SET_1D3  , 2, 'SET 2,E'    ),
            (SET_1D4  , 2, 'SET 2,H'    ),(SET_1D5  , 2, 'SET 2,L'    ),(SET_1D6  , 2, 'SET 2,(HL)' ),(SET_1D7  , 2, 'SET 2,A'    ),
            (SET_1D8  , 2, 'SET 3,B'    ),(SET_1D9  , 2, 'SET 3,C'    ),(SET_1DA  , 2, 'SET 3,D'    ),(SET_1DB  , 2, 'SET 3,E'    ),
            (SET_1DC  , 2, 'SET 3,H'    ),(SET_1DD  , 2, 'SET 3,L'    ),(SET_1DE  , 2, 'SET 3,(HL)' ),(SET_1DF  , 2, 'SET 3,A'    ),
            # 1Ex
            (SET_1E0  , 2, 'SET 4,B'    ),(SET_1E1  , 2, 'SET 4,C'    ),(SET_1E2  , 2, 'SET 4,D'    ),(SET_1E3  , 2, 'SET 4,E'    ),
            (SET_1E4  , 2, 'SET 4,H'    ),(SET_1E5  , 2, 'SET 4,L'    ),(SET_1E6  , 2, 'SET 4,(HL)' ),(SET_1E7  , 2, 'SET 4,A'    ),
            (SET_1E8  , 2, 'SET 5,B'    ),(SET_1E9  , 2, 'SET 5,C'    ),(SET_1EA  , 2, 'SET 5,D'    ),(SET_1EB  , 2, 'SET 5,E'    ),
            (SET_1EC  , 2, 'SET 5,H'    ),(SET_1ED  , 2, 'SET 5,L'    ),(SET_1EE  , 2, 'SET 5,(HL)' ),(SET_1EF  , 2, 'SET 5,A'    ),
            # 1Fx
            (SET_1F0  , 2, 'SET 6,B'    ),(SET_1F1  , 2, 'SET 6,C'    ),(SET_1F2  , 2, 'SET 6,D'    ),(SET_1F3  , 2, 'SET 6,E'    ),
            (SET_1F4  , 2, 'SET 6,H'    ),(SET_1F5  , 2, 'SET 6,L'    ),(SET_1F6  , 2, 'SET 6,(HL)' ),(SET_1F7  , 2, 'SET 6,A'    ),
            (SET_1F8  , 2, 'SET 7,B'    ),(SET_1F9  , 2, 'SET 7,C'    ),(SET_1FA  , 2, 'SET 7,D'    ),(SET_1FB  , 2, 'SET 7,E'    ),
            (SET_1FC  , 2, 'SET 7,H'    ),(SET_1FD  , 2, 'SET 7,L'    ),(SET_1FE  , 2, 'SET 7,(HL)' ),(SET_1FF  , 2, 'SET 7,A'    )
        ]
    
    @property
    def Fc(self) -> bool: return bool((self.F >> FLAG_C) & 1)
    @property
    def Fh(self) -> bool: return bool((self.F >> FLAG_H) & 1)
    @property
    def Fn(self) -> bool: return bool((self.F >> FLAG_N) & 1)
    @property
    def Fz(self) -> bool: return bool((self.F >> FLAG_Z) & 1)

    @property
    def AF(self) -> int: return ((self.A << 8) | self.F) & 0xFFFF
    @property
    def BC(self) -> int: return ((self.B << 8) | self.C) & 0xFFFF
    @property
    def DE(self) -> int: return ((self.D << 8) | self.E) & 0xFFFF
    @property
    def HL(self) -> int: return ((self.H << 8) | self.L) & 0xFFFF

    # structure of the stack
    #   +   ______ (bottom)
    #       _sth__
    #       _sth__
    # SP -> _null_ (top)

    def pop(self) -> int:
        val = self.emu.read(self.SP)
        self.SP += 1
        return val
    
    def push(self, byte: int) -> None:
        self.SP -= 1
        self.emu.write(self.SP, byte)
    
    def fetchAndExec(self) -> int:
        # fetch a new opcode
        self.opcode = self.emu.read(self.PC)
        if self.opcode == 0xCB:
            # extension code
            self.opcode = 0x100 + self.emu.read(self.PC + 1)

        # decode
        try:
            opfunc, oplen, self.opname = self.OP_MAP[self.opcode]
            for i in range(oplen - 1):
                self.args[i] = self.emu.read(self.PC + 1 + i)
        except IndexError:
            print(f'opcode: {toHex(self.opcode)} is not in the OP_MAP')
            return 0
        
        # execute
        self.PC += oplen
        cyclesPassed = opfunc(self)
        self.PC &= 0xFFFF
        return cyclesPassed
    
    def setInterrupt(self, flag: int) -> None:
        self.emu.write(IF_ADDR, self.emu.read(IF_ADDR) | (1 << flag))
    
    def handleInterrupted(self) -> bool:
        if not self.interruptable:
            return False
        
        IF, IE = self.emu.read(IF_ADDR), self.emu.read(IE_ADDR)
        for flag in range(5):
            if (IF & (1 << flag)) and (IE & (1 << flag)):
                # clear interrupt flag
                self.emu.write(IF_ADDR, self.emu.read(IF_ADDR) & (0xFF - (1 << flag)))
                self.interruptable = False
                self.push(self.PC >> 8) # high addr
                self.push(self.PC & 0xFF) # low addr
                break
        else:
            return False
        
        if flag == IF_VBLANK:
            self.PC = 0x0040
        elif flag == IF_STAT:
            self.PC = 0x0048
        elif flag == IF_TIMER:
            self.PC = 0x0050
        elif flag == IF_SERIAL:
            self.PC = 0x0058
        elif flag == IF_JOYPAD:
            self.PC = 0x0060
        return True
    
    def step(self) -> int:
        if self.halted:
            if self.handleInterrupted():
                self.halted = False
            else:
                return 4
        return self.fetchAndExec()

############
# op codes #
############

# 0xXX : NULL
def NULL(z80: Z80) -> int:
    print('*** NULL ***')
    return 0

# 0x00 : NOP
# - - - -
def NOP_00(z80: Z80) -> int:
    # print('*** NOP ***')
    return 4

# 0x01 : LD BC, d16
# - - - -
def LD_01(z80: Z80) -> int:
    z80.B = z80.args[1]
    z80.C = z80.args[0]
    return 12

# 0x02 : LD (BC), A
# - - - -
def LD_02(z80: Z80) -> int:
    z80.emu.write(z80.BC, z80.A)
    return 8

# 0x03 : INC BC
# - - - -
def INC_03(z80: Z80) -> int:
    val = (z80.BC + 1) & 0xFFFF
    z80.B = val >> 8
    z80.C = val & 0xFF
    return 8

def INC_inner(z80: Z80, reg: int) -> int:
    flag = 0b00000000

    # set flag H to 1 if carry from bit 3
    flag |= ((reg & 0xF) == 0xF) << FLAG_H

    reg = (reg + 1) & 0xFF
    # set flag Z to 1 if results 0
    flag |= (reg == 0) << FLAG_Z

    z80.F &= 0b00010000
    z80.F |= flag
    return reg

# 0x04 : INC B
# Z 0 H -
def INC_04(z80: Z80) -> int:
    z80.B = INC_inner(z80, z80.B)
    return 4

def DEC_inner(z80: Z80, reg: int) -> int:
    flag = 0b01000000

    # set flag H to 1 if not borrow from bit 4
    flag |= ((reg & 0xF) < 1) << FLAG_H

    reg = (reg - 1) & 0xFF
    # set flag Z to 1 if results 0
    flag |= (reg == 0) << FLAG_Z

    z80.F &= 0b00010000
    z80.F |= flag
    return reg

# 0x05 : DEC B
# Z 1 H -
def DEC_05(z80: Z80) -> int:
    z80.B = DEC_inner(z80, z80.B)
    return 4

# 0x06 : LD B, d8
# - - - -
def LD_06(z80: Z80) -> int:
    z80.B = z80.args[0]
    return 8

# 0x07 : RLCA : rotate A left, old bit 7 to carry flag
# 0 0 0 C
def RLCA_07(z80: Z80) -> int:
    val = (z80.A << 1) | (z80.A >> 7)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 4

# 0x08 : LD (a16), SP
# - - - -
def LD_08(z80: Z80) -> int:
    a16 = (z80.args[1] << 8) | z80.args[0]
    z80.emu.write(a16, z80.SP & 0xFF)
    z80.emu.write(a16 + 1, z80.SP >> 8)
    return 20

# 0x09 : ADD HL, BC
# - 0 H C
def ADD_09(z80: Z80) -> int:
    val = z80.HL + z80.BC
    flag = 0b00000000

    # set flag H to 1 if carry from bit 11
    flag |= (((z80.HL & 0xFFF) + (z80.BC & 0xFFF)) > 0xFFF) << FLAG_H
    # set flag C to 1 if carry from bit 15
    flag |= (val > 0xFFFF) << FLAG_C

    z80.H = (val >> 8) & 0xFF
    z80.L = val & 0xFF
    z80.F &= 0b10000000
    z80.F |= flag
    return 8

# 0x0A : LD A, (BC)
# - - - -
def LD_0A(z80: Z80) -> int:
    z80.A = z80.emu.read(z80.BC)
    return 8

# 0x0B : DEC BC
# - - - -
def DEC_0B(z80: Z80) -> int:
    val = (z80.BC - 1) & 0xFFFF
    z80.B = val >> 8
    z80.C = val & 0xFF
    return 8

# 0x0C : INC C
# Z 0 H -
def INC_0C(z80: Z80) -> int:
    z80.C = INC_inner(z80, z80.C)
    return 4

# 0x0D : DEC C
# Z 1 H -
def DEC_0D(z80: Z80) -> int:
    z80.C = DEC_inner(z80, z80.C)
    return 4

# 0x0E : LD C, d8
# - - - -
def LD_0E(z80: Z80) -> int:
    z80.C = z80.args[0]
    return 8

# 0x0F : RRCA : rotate A right, old bit 0 to carry flag
# 0 0 0 C
def RRCA_0F(z80: Z80) -> int:
    val = (z80.A >> 1) | ((z80.A & 1) << 7) | ((z80.A & 1) << 8)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 4

# 0x10 : STOP 0
# - - - -
def STOP_10(z80: Z80) -> int:
    print('*** STOP ***')
    return 4

# 0x11 : LD DE, d16
# - - - -
def LD_11(z80: Z80) -> int:
    z80.D = z80.args[1]
    z80.E = z80.args[0]
    return 12

# 0x12 : LD (DE), A
# - - - -
def LD_12(z80: Z80) -> int:
    z80.emu.write(z80.DE, z80.A)
    return 8

# 0x13 : INC DE
# - - - -
def INC_13(z80: Z80) -> int:
    val = (z80.DE + 1) & 0xFFFF
    z80.D = val >> 8
    z80.E = val & 0xFF
    return 8

# 0x14 : INC D
# Z 0 H -
def INC_14(z80: Z80) -> int:
    z80.D = INC_inner(z80, z80.D)
    return 4

# 0x15 : DEC D
# Z 1 H -
def DEC_15(z80: Z80) -> int:
    z80.D = DEC_inner(z80, z80.D)
    return 4

# 0x16 : LD D, d8
# - - - -
def LD_16(z80: Z80) -> int:
    z80.D = z80.args[0]
    return 8

# 0x17 : RLA : rotate A left through carry flag
# 0 0 0 C
def RLA_17(z80: Z80) -> int:
    val = (z80.A << 1) | z80.Fc
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 4

# 0x18 : JR r8 : add signed data current address and jump to it
# - - - -
def JR_18(z80: Z80) -> int:
    z80.PC += z80.args[0]
    # 1 at msb (-)
    if z80.args[0] & 0x80:
        z80.PC -= 0x100
    return 12

# 0x19 : ADD HL, DE
# - 0 H C
def ADD_19(z80: Z80) -> int:
    val = z80.HL + z80.DE
    flag = 0b00000000

    # set flag H to 1 if carry from bit 11
    flag |= (((z80.HL & 0xFFF) + (z80.BC & 0xFFF)) > 0xFFF) << FLAG_H
    # set flag C to 1 if carry from bit 15
    flag |= (val > 0xFFFF) << FLAG_C

    z80.H = (val >> 8) & 0xFF
    z80.L = val & 0xFF
    z80.F &= 0b10000000
    z80.F |= flag
    return 8

# 0x1A : LD A, (DE)
# - - - -
def LD_1A(z80: Z80) -> int:
    z80.A = z80.emu.read(z80.DE)
    return 8

# 0x1B : DEC DE
# - - - -
def DEC_1B(z80: Z80) -> int:
    val = (z80.DE - 1) & 0xFFFF
    z80.D = val >> 8
    z80.E = val & 0xFF
    return 8

# 0x1C : INC E
# Z 0 H -
def INC_1C(z80: Z80) -> int:
    z80.E = INC_inner(z80, z80.E)
    return 4

# 0x1D : DEC E
# Z 1 H -
def DEC_1D(z80: Z80) -> int:
    z80.E = DEC_inner(z80, z80.E)
    return 4

# 0x1E : LD E, d8
# - - - -
def LD_1E(z80: Z80) -> int:
    z80.E = z80.args[0]
    return 8

# 0x1F : RRA : rotate A right through carray flag
# 0 0 0 C
def RRA_1F(z80: Z80) -> int:
    val = (z80.A >> 1) | ((z80.A & 1) << 8) | (z80.Fc << 7)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 4

# 0x20 : JR NZ, r8 : jump if flag Z is 0
# - - - -
def JR_20(z80: Z80) -> int:
    if z80.Fz:
        return 8
    else:
        z80.PC += z80.args[0]
        # 1 at msb (-)
        if z80.args[0] & 0x80:
            z80.PC -= 0x100
        return 12

# 0x21 : LD HL, d16
# - - - -
def LD_21(z80: Z80) -> int:
    z80.H = z80.args[1]
    z80.L = z80.args[0]
    return 12

# 0x22 : LD (HL+), A : load into memory address HL, increment HL
# - - - -
def LD_22(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.A)
    val = (z80.HL + 1) & 0xFFFF
    z80.H = val >> 8
    z80.L = val & 0xFF
    return 8

# 0x23 : INC HL
# - - - -
def INC_23(z80: Z80) -> int:
    val = (z80.HL + 1) & 0xFFFF
    z80.H = val >> 8
    z80.L = val & 0xFF
    return 8

# 0x24 : INC H
# Z 0 H -
def INC_24(z80: Z80) -> int:
    z80.H = INC_inner(z80, z80.H)
    return 4

# 0x25 : DEC H
# Z 1 H -
def DEC_25(z80: Z80) -> int:
    z80.H = DEC_inner(z80, z80.H)
    return 4

# 0x26 : LD H, d8
# - - - -
def LD_26(z80: Z80) -> int:
    z80.H = z80.args[0]
    return 8

# 0x27 : DAA : decimal adjust reg A
# Z - 0 C
def DAA_27(z80: Z80) -> int:
    val = z80.A
    flag = 0b00000000

    if z80.Fn:
        if z80.Fh: val = (val - 0x06) & 0xFF
        if z80.Fc: val = (val - 0x60) & 0xFF
    else:
        if z80.Fh or (val & 0x0F) > 0x09: val += 0x06
        if z80.Fc or val > 0x9F: val += 0x60
    
    flag |= ((val & 0xFF) == 0) << FLAG_Z
    flag |= (val > 0xFF) << FLAG_C
    '''
    val = z80.A
    flag = 0b00000000

    correction = 0
    correction |= 0x06 if z80.Fh else 0x00
    correction |= 0x60 if z80.Fc else 0x00

    if z80.Fn:
        val -= correction
    else:
        correction |= 0x06 if (val & 0x0F) > 0x09 else 0x00
        correction |= 0x60 if val > 0x99 else 0x00
        val += correction
    
    flag |= ((val & 0xFF) == 0) << FLAG_Z
    flag |= (correction & 0x60 != 0) << FLAG_C
    '''
    z80.A = val & 0xFF
    z80.F &= 0b01000000
    z80.F |= flag
    return 4

# 0x28 : JR Z, r8 : jump if flag Z is 1
# - - - -
def JR_28(z80: Z80) -> int:
    if z80.Fz:
        z80.PC += z80.args[0]
        # 1 at msb (-)
        if z80.args[0] & 0x80:
            z80.PC -= 0x100
        return 12
    else:
        return 8

# 0x29 : ADD HL, HL
# - 0 H C
def ADD_29(z80: Z80) -> int:
    val = z80.HL + z80.HL
    flag = 0b00000000

    # set flag H to 1 if carry from bit 11
    flag |= (((z80.HL & 0xFFF) + (z80.HL & 0xFFF)) > 0xFFF) << FLAG_H
    # set flag C to 1 if  carry from bit 15
    flag |= (val > 0xFFFF) << FLAG_C

    z80.H = (val >> 8) & 0xFF
    z80.L = val & 0xFF
    z80.F &= 0b10000000
    z80.F |= flag
    return 8

# 0x2A : LD A, (HL+)
# - - - -
def LD_2A(z80: Z80) -> int:
    z80.A = z80.emu.read(z80.HL)
    val = (z80.HL + 1) & 0xFFFF
    z80.H = val >> 8
    z80.L = val & 0xFF
    return 8

# 0x2B : DEC HL
# - - - -
def DEC_2B(z80: Z80) -> int:
    val = (z80.HL - 1) & 0xFFFF
    z80.H = val >> 8
    z80.L = val & 0xFF
    return 8

# 0x2C : INC L
# Z 0 H -
def INC_2C(z80: Z80) -> int:
    z80.L = INC_inner(z80, z80.L)
    return 4

# 0x2D : DEC L
# Z 1 H -
def DEC_2D(z80: Z80) -> int:
    z80.L = DEC_inner(z80, z80.L)
    return 4

# 0x2E : LD L, d8
# - - - -
def LD_2E(z80: Z80) -> int:
    z80.L = z80.args[0]
    return 8

# 0x2F : CPL : complement reg A (flip all bits)
# - 1 1 -
def CPL_2F(z80: Z80) -> int:
    val = (~z80.A) & 0xFF
    flag = 0b01100000

    z80.A = val
    z80.F &= 0b10010000
    z80.F |= flag
    return 4

# 0x30 : JR NC, r8 : jump if flag C is 0
# - - - -
def JR_30(z80: Z80) -> int:
    if z80.Fc:
        return 8
    else:
        z80.PC += z80.args[0]
        # 1 at msb (-)
        if z80.args[0] & 0x80:
            z80.PC -= 0x100
        return 12

# 0x31 : LD SP, d16
# - - - -
def LD_31(z80: Z80) -> int:
    z80.SP = (z80.args[1] << 8) | z80.args[0]
    return 12

# 0x32 : LD (HL-), A
# - - - -
def LD_32(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.A)
    val = (z80.HL - 1) & 0xFFFF
    z80.H = val >> 8
    z80.L = val & 0xFF
    return 8

# 0x33 : INC SP
# - - - -
def INC_33(z80: Z80) -> int:
    z80.SP = (z80.SP + 1) & 0xFFFF
    return 8

# 0x34 : INC (HL)
# Z 0 H -
def INC_34(z80: Z80) -> int:
    z80.emu.write(z80.HL, INC_inner(z80, z80.emu.read(z80.HL)))
    return 12

# 0x35 : DEC (HL)
# Z 1 H -
def DEC_35(z80: Z80) -> int:
    z80.emu.write(z80.HL, DEC_inner(z80, z80.emu.read(z80.HL)))
    return 12

# 0x36 : LD (HL), d8
# - - - -
def LD_36(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.args[0])
    return 12

# 0x37 : SCF : set carry flag
# - 0 0 1
def SCF_37(z80: Z80) -> int:
    z80.F &= 0b10000000
    z80.F |= 0b00010000
    return 4

# 0x38 : JR C, r8 : jump if flag C is 1
# - - - -
def JR_38(z80: Z80) -> int:
    if z80.Fc:
        z80.PC += z80.args[0]
        # 1 at msb (-)
        if z80.args[0] & 0x80:
            z80.PC -= 0x100
        return 12
    else:
        return 8
    
# 0x39 : ADD HL, SP
# - 0 H C
def ADD_39(z80: Z80) -> int:
    val = z80.HL + z80.SP
    flag = 0b00000000

    # set flag H to 1 if carry from bit 11
    flag |= (((z80.HL & 0xFFF) + (z80.SP & 0xFFF)) > 0xFFF) << FLAG_H
    # set flag C to 1 if  carry from bit 15
    flag |= (val > 0xFFFF) << FLAG_C

    z80.H = (val >> 8) & 0xFF
    z80.L = val & 0xFF
    z80.F &= 0b10000000
    z80.F |= flag
    return 8

# 0x3A : LD A, (HL-)
# - - - -
def LD_3A(z80: Z80) -> int:
    z80.A = z80.emu.read(z80.HL)
    val = (z80.HL - 1) & 0xFFFF
    z80.H = val >> 8
    z80.L = val & 0xFF
    return 8

# 0x3B : DEC SP
# - - - -
def DEC_3B(z80: Z80) -> int:
    z80.SP = (z80.SP - 1) & 0xFFFF
    return 8

# 0x3C : INC A
# Z 0 H -
def INC_3C(z80: Z80) -> int:
    z80.A = INC_inner(z80, z80.A)
    return 4

# 0x3D : DEC A
# Z 1 H -
def DEC_3D(z80: Z80) -> int:
    z80.A = DEC_inner(z80, z80.A)
    return 4

# 0x3E : LD A, d8
# - - - -
def LD_3E(z80: Z80) -> int:
    z80.A = z80.args[0]
    return 8

# 0x3F : CCF : carry complement flag
# - 0 0 C
def CCF_3F(z80: Z80) -> int:
    flag = (z80.F & 0b00010000) ^ 0b00010000
    z80.F &= 0b10000000
    z80.F |= flag
    return 4

# 0x40 : LD B, B
# - - - -
def LD_40(z80: Z80) -> int:
    z80.B = z80.B
    return 4

# 0x41 : LD B, C
# - - - -
def LD_41(z80: Z80) -> int:
    z80.B = z80.C
    return 4

# 0x42 : LD B, D
# - - - -
def LD_42(z80: Z80) -> int:
    z80.B = z80.D
    return 4

# 0x43 : LD B, E
# - - - -
def LD_43(z80: Z80) -> int:
    z80.B = z80.E
    return 4

# 0x44 : LD B, H
# - - - -
def LD_44(z80: Z80) -> int:
    z80.B = z80.H
    return 4

# 0x45 : LD B, L
# - - - -
def LD_45(z80: Z80) -> int:
    z80.B = z80.L
    return 4

# 0x46 : LD B, (HL)
# - - - -
def LD_46(z80: Z80) -> int:
    z80.B = z80.emu.read(z80.HL)
    return 8

# 0x47 : LD B, A
# - - - -
def LD_47(z80: Z80) -> int:
    z80.B = z80.A
    return 4

# 0x48 : LD C, B
# - - - -
def LD_48(z80: Z80) -> int:
    z80.C = z80.B
    return 4

# 0x49 : LD C, C
# - - - -
def LD_49(z80: Z80) -> int:
    z80.C = z80.C
    return 4

# 0x4A : LD C, D
# - - - -
def LD_4A(z80: Z80) -> int:
    z80.C = z80.D
    return 4

# 0x4B : LD C, E
# - - - -
def LD_4B(z80: Z80) -> int:
    z80.C = z80.E
    return 4

# 0x4C : LD C, H
# - - - -
def LD_4C(z80: Z80) -> int:
    z80.C = z80.H
    return 4

# 0x4D : LD C, L
# - - - -
def LD_4D(z80: Z80) -> int:
    z80.C = z80.L
    return 4

# 0x4E : LD C, (HL)
# - - - -
def LD_4E(z80: Z80) -> int:
    z80.C = z80.emu.read(z80.HL)
    return 8

# 0x4F : LD C, A
# - - - -
def LD_4F(z80: Z80) -> int:
    z80.C = z80.A
    return 4

# 0x50 : LD D, B
# - - - -
def LD_50(z80: Z80) -> int:
    z80.D = z80.B
    return 4

# 0x51 : LD D, C
# - - - -
def LD_51(z80: Z80) -> int:
    z80.D = z80.C
    return 4

# 0x52 : LD D, D
# - - - -
def LD_52(z80: Z80) -> int:
    z80.D = z80.D
    return 4

# 0x53 : LD D, E
# - - - -
def LD_53(z80: Z80) -> int:
    z80.D = z80.E
    return 4

# 0x54 : LD D, H
# - - - -
def LD_54(z80: Z80) -> int:
    z80.D = z80.H
    return 4

# 0x55 : LD D, L
# - - - -
def LD_55(z80: Z80) -> int:
    z80.D = z80.L
    return 4

# 0x56 : LD D, (HL)
# - - - -
def LD_56(z80: Z80) -> int:
    z80.D = z80.emu.read(z80.HL)
    return 8

# 0x57 : LD D, A
# - - - -
def LD_57(z80: Z80) -> int:
    z80.D = z80.A
    return 4

# 0x58 : LD E, B
# - - - -
def LD_58(z80: Z80) -> int:
    z80.E = z80.B
    return 4

# 0x59 : LD E, C
# - - - -
def LD_59(z80: Z80) -> int:
    z80.E = z80.C
    return 4

# 0x5A : LD E, D
# - - - -
def LD_5A(z80: Z80) -> int:
    z80.E = z80.D
    return 4

# 0x5B : LD E, E
# - - - -
def LD_5B(z80: Z80) -> int:
    z80.E = z80.E
    return 4

# 0x5C : LD E, H
# - - - -
def LD_5C(z80: Z80) -> int:
    z80.E = z80.H
    return 4

# 0x5D : LD E, L
# - - - -
def LD_5D(z80: Z80) -> int:
    z80.E = z80.L
    return 4

# 0x5E : LD E, (HL)
# - - - -
def LD_5E(z80: Z80) -> int:
    z80.E = z80.emu.read(z80.HL)
    return 8

# 0x5F : LD E, A
# - - - -
def LD_5F(z80: Z80) -> int:
    z80.E = z80.A
    return 4

# 0x60 : LD H, B
# - - - -
def LD_60(z80: Z80) -> int:
    z80.H = z80.B
    return 4

# 0x61 : LD H, C
# - - - -
def LD_61(z80: Z80) -> int:
    z80.H = z80.C
    return 4

# 0x62 : LD H, D
# - - - -
def LD_62(z80: Z80) -> int:
    z80.H = z80.D
    return 4

# 0x63 : LD H, E
# - - - -
def LD_63(z80: Z80) -> int:
    z80.H = z80.E
    return 4

# 0x64 : LD H, H
# - - - -
def LD_64(z80: Z80) -> int:
    z80.H = z80.H
    return 4

# 0x65 : LD H, L
# - - - -
def LD_65(z80: Z80) -> int:
    z80.H = z80.L
    return 4

# 0x66 : LD H, (HL)
# - - - -
def LD_66(z80: Z80) -> int:
    z80.H = z80.emu.read(z80.HL)
    return 8

# 0x67 : LD H, A
# - - - -
def LD_67(z80: Z80) -> int:
    z80.H = z80.A
    return 4

# 0x68 : LD L, B
# - - - -
def LD_68(z80: Z80) -> int:
    z80.L = z80.B
    return 4

# 0x69 : LD L, C
# - - - -
def LD_69(z80: Z80) -> int:
    z80.L = z80.C
    return 4

# 0x6A : LD L, D
# - - - -
def LD_6A(z80: Z80) -> int:
    z80.L = z80.D
    return 4

# 0x6B : LD L, E
# - - - -
def LD_6B(z80: Z80) -> int:
    z80.L = z80.E
    return 4

# 0x6C : LD L, H
# - - - -
def LD_6C(z80: Z80) -> int:
    z80.L = z80.H
    return 4

# 0x6D : LD L, L
# - - - -
def LD_6D(z80: Z80) -> int:
    z80.L = z80.L
    return 4

# 0x6E : LD L, (HL)
# - - - -
def LD_6E(z80: Z80) -> int:
    z80.L = z80.emu.read(z80.HL)
    return 8

# 0x6F : LD L, A
# - - - -
def LD_6F(z80: Z80) -> int:
    z80.L = z80.A
    return 4

# 0x70 : LD (HL), B
# - - - -
def LD_70(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.B)
    return 8

# 0x71 : LD (HL), C
# - - - -
def LD_71(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.C)
    return 8

# 0x72 : LD (HL), D
# - - - -
def LD_72(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.D)
    return 8

# 0x73 : LD (HL), E
# - - - -
def LD_73(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.E)
    return 8

# 0x74 : LD (HL), H
# - - - -
def LD_74(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.H)
    return 8

# 0x75 : LD (HL), L
# - - - -
def LD_75(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.L)
    return 8

# 0x76 : HALT
# - - - -
def HALT_76(z80: Z80) -> int:
    print(f'*** HALT *** ({toHex(z80.PC)})')
    if z80.interruptable:
        z80.halted = True
    return 4

# 0x77 : LD (HL), A
# - - - -
def LD_77(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.A)
    return 8

# 0x78 : LD A, B
# - - - -
def LD_78(z80: Z80) -> int:
    z80.A = z80.B
    return 4

# 0x79 : LD A, C
# - - - -
def LD_79(z80: Z80) -> int:
    z80.A = z80.C
    return 4

# 0x7A : LD A, D
# - - - -
def LD_7A(z80: Z80) -> int:
    z80.A = z80.D
    return 4

# 0x7B : LD A, E
# - - - -
def LD_7B(z80: Z80) -> int:
    z80.A = z80.E
    return 4

# 0x7C : LD A, H
# - - - -
def LD_7C(z80: Z80) -> int:
    z80.A = z80.H
    return 4

# 0x7D : LD A, L
# - - - -
def LD_7D(z80: Z80) -> int:
    z80.A = z80.L
    return 4

# 0x7E : LD A, (HL)
# - - - -
def LD_7E(z80: Z80) -> int:
    z80.A = z80.emu.read(z80.HL)
    return 8

# 0x7F : LD A, A
# - - - -
def LD_7F(z80: Z80) -> int:
    z80.A = z80.A
    return 4

def ADD_inner(z80: Z80, reg: int) -> int:
    val = z80.A + reg
    flag = 0b00000000

    # set flag H to 1 if carry from bit 3
    flag |= (((z80.A & 0xF) + (reg & 0xF)) > 0xF) << FLAG_H
    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x80 : ADD A, B
# Z 0 H C
def ADD_80(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.B)
    return 4

# 0x81 : ADD A, C
# Z 0 H C
def ADD_81(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.C)
    return 4

# 0x82 : ADD A, D
# Z 0 H C
def ADD_82(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.D)
    return 4

# 0x83 : ADD A, E
# Z 0 H C
def ADD_83(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.E)
    return 4

# 0x84 : ADD A, H
# Z 0 H C
def ADD_84(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.H)
    return 4

# 0x85 : ADD A, L
# Z 0 H C
def ADD_85(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.L)
    return 4

# 0x86 : ADD A, (HL)
# Z 0 H C
def ADD_86(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0x87 : ADD A, A
# Z 0 H C
def ADD_87(z80: Z80) -> int:
    z80.A = ADD_inner(z80, z80.A)
    return 4

def ADC_inner(z80: Z80, reg: int) -> int:
    val = z80.A + reg + z80.Fc
    flag = 0b00000000

    # set flag H to 1 if carry from bit 3
    flag |= (((z80.A & 0xF) + (reg & 0xF) + z80.Fc) > 0xF) << FLAG_H
    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= (val & 0xFF == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x88 : ADC A, B
# Z 0 H C
def ADC_88(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.B)
    return 4

# 0x89 : ADC A, C
# Z 0 H C
def ADC_89(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.C)
    return 4

# 0x8A : ADC A, D
# Z 0 H C
def ADC_8A(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.D)
    return 4

# 0x8B : ADC A, E
# Z 0 H C
def ADC_8B(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.E)
    return 4

# 0x8C : ADC A, H
# Z 0 H C
def ADC_8C(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.H)
    return 4

# 0x8D : ADC A, L
# Z 0 H C
def ADC_8D(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.L)
    return 4

# 0x8E : ADC A, (HL)
# Z 0 H C
def ADC_8E(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0x8F : ADC A, A
# Z 0 H C
def ADC_8F(z80: Z80) -> int:
    z80.A = ADC_inner(z80, z80.A)
    return 4

def SUB_inner(z80: Z80, reg: int) -> int:
    val = z80.A - reg
    flag = 0b01000000
    
    # set flag H to 1 if borrow from bit 4
    flag |= ((z80.A & 0xF) < (reg & 0xF)) << FLAG_H
    # set flag C to 1 if borrow from bit 8
    flag |= (val < 0) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= (val & 0xFF == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x90 : SUB B
# Z 1 H C
def SUB_90(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.B)
    return 4

# 0x91 : SUB C
# Z 1 H C
def SUB_91(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.C)
    return 4

# 0x92 : SUB D
# Z 1 H C
def SUB_92(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.D)
    return 4

# 0x93 : SUB E
# Z 1 H C
def SUB_93(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.E)
    return 4

# 0x94 : SUB H
# Z 1 H C
def SUB_94(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.H)
    return 4

# 0x95 : SUB L
# Z 1 H C
def SUB_95(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.L)
    return 4

# 0x96 : SUB (HL)
# Z 1 H C
def SUB_96(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0x97 : SUB A
# Z 1 H C
def SUB_97(z80: Z80) -> int:
    z80.A = SUB_inner(z80, z80.A)
    return 4

def SBC_inner(z80: Z80, reg: int) -> int:
    val = z80.A - reg - z80.Fc
    flag = 0b01000000

    # set flag H to 1 if borrow from bit 4
    flag |= (((z80.A & 0xF) - (reg & 0xF) - z80.Fc) < 0) << FLAG_H
    # set flag C to 1 if borrow from bit 8
    flag |= (val < 0) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= (val & 0xFF == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x98 : SBC A, B
# Z 1 H C
def SBC_98(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.B)
    return 4

# 0x99 : SBC A, C
# Z 1 H C
def SBC_99(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.C)
    return 4

# 0x9A : SBC A, D
# Z 1 H C
def SBC_9A(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.D)
    return 4

# 0x9B : SBC A, E
# Z 1 H C
def SBC_9B(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.E)
    return 4

# 0x9C : SBC A, H
# Z 1 H C
def SBC_9C(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.H)
    return 4

# 0x9D : SBC A, L
# Z 1 H C
def SBC_9D(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.L)
    return 4

# 0x9E : SBC A, (HL)
# Z 1 H C
def SBC_9E(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0x9F : SBC A, A
# Z 1 H C
def SBC_9F(z80: Z80) -> int:
    z80.A = SBC_inner(z80, z80.A)
    return 4

def AND_inner(z80: Z80, reg: int) -> int:
    val = (z80.A & reg) & 0xFF
    flag = 0b00100000

    # set flag Z to 1 if results 0
    flag |= (val == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val

# 0xA0 : AND B
# Z 0 1 0
def AND_A0(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.B)
    return 4

# 0xA1 : AND C
# Z 0 1 0
def AND_A1(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.C)
    return 4

# 0xA2 : AND D
# Z 0 1 0
def AND_A2(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.D)
    return 4

# 0xA3 : AND E
# Z 0 1 0
def AND_A3(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.E)
    return 4

# 0xA4 : AND H
# Z 0 1 0
def AND_A4(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.H)
    return 4

# 0xA5 : AND L
# Z 0 1 0
def AND_A5(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.L)
    return 4

# 0xA6 : AND (HL)
# Z 0 1 0
def AND_A6(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0xA7 : AND A
# Z 0 1 0
def AND_A7(z80: Z80) -> int:
    z80.A = AND_inner(z80, z80.A)
    return 4

def XOR_inner(z80: Z80, reg: int) -> int:
    val = (z80.A ^ reg) & 0xFF
    flag = 0b00000000

    # set flag Z to 1 if results 0
    flag |= (val == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val

# 0xA8 : XOR B
# Z 0 0 0
def XOR_A8(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.B)
    return 4

# 0xA9 : XOR C
# Z 0 0 0
def XOR_A9(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.C)
    return 4

# 0xAA : XOR D
# Z 0 0 0
def XOR_AA(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.D)
    return 4

# 0xAB : XOR E
# Z 0 0 0
def XOR_AB(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.E)
    return 4

# 0xAC : XOR H
# Z 0 0 0
def XOR_AC(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.H)
    return 4

# 0xAD : XOR L
# Z 0 0 0
def XOR_AD(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.L)
    return 4

# 0xAE : XOR (HL)
# Z 0 0 0
def XOR_AE(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0xAF : XOR A
# Z 0 0 0
def XOR_AF(z80: Z80) -> int:
    z80.A = XOR_inner(z80, z80.A)
    return 4

def OR_inner(z80: Z80, reg: int) -> int:
    val = (z80.A | reg) & 0xFF
    flag = 0b00000000

    # set flag Z to 1 if results 0
    flag |= (val == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val

# 0xB0 : OR B
# Z 0 0 0
def OR_B0(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.B)
    return 4

# 0xB1 : OR C
# Z 0 0 0
def OR_B1(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.C)
    return 4

# 0xB2 : OR D
# Z 0 0 0
def OR_B2(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.D)
    return 4

# 0xB3 : OR E
# Z 0 0 0
def OR_B3(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.E)
    return 4

# 0xB4 : OR H
# Z 0 0 0
def OR_B4(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.H)
    return 4

# 0xB5 : OR L
# Z 0 0 0
def OR_B5(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.L)
    return 4

# 0xB6 : OR (HL)
# Z 0 0 0
def OR_B6(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0xB7 : OR A
# Z 0 0 0
def OR_B7(z80: Z80) -> int:
    z80.A = OR_inner(z80, z80.A)
    return 4

def CP_inner(z80: Z80, reg: int) -> None:
    val = z80.A - reg
    flag = 0b01000000

    # set flag H to 1 if borrow from bit 4
    flag |= ((z80.A & 0xF) < (reg & 0xF)) << FLAG_H
    # set flag C to 1 if borrow from bit 8
    flag |= (val < 0) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag

# 0xB8 : CP B : compare reg A with reg B (value of subtraction won't be stored)
# Z 1 H C
def CP_B8(z80: Z80) -> int:
    CP_inner(z80, z80.B)
    return 4

# 0xB9 : CP C
# Z 1 H C
def CP_B9(z80: Z80) -> int:
    CP_inner(z80, z80.C)
    return 4

# 0xBA : CP D
# Z 1 H C
def CP_BA(z80: Z80) -> int:
    CP_inner(z80, z80.D)
    return 4

# 0xBB : CP E
# Z 1 H C
def CP_BB(z80: Z80) -> int:
    CP_inner(z80, z80.E)
    return 4

# 0xBC : CP H
# Z 1 H C
def CP_BC(z80: Z80) -> int:
    CP_inner(z80, z80.H)
    return 4

# 0xBD : CP L
# Z 1 H C
def CP_BD(z80: Z80) -> int:
    CP_inner(z80, z80.L)
    return 4

# 0xBE : CP (HL)
# Z 1 H C
def CP_BE(z80: Z80) -> int:
    CP_inner(z80, z80.emu.read(z80.HL))
    return 8

# 0xBF : CP A
# Z 1 H C
def CP_BF(z80: Z80) -> int:
    CP_inner(z80, z80.A)
    return 4

# 0xC0 : RET NZ : return if flag Z is 0
# - - - -
def RET_C0(z80: Z80) -> int:
    if z80.Fz:
        return 8
    else:
        addrLo = z80.pop()
        addrHi = z80.pop()
        z80.PC = (addrHi << 8) | addrLo
        return 20

# 0xC1 : POP BC
# - - - -
def POP_C1(z80: Z80) -> int:
    z80.C = z80.pop()
    z80.B = z80.pop()
    return 12

# 0xC2 : JP NZ, a16
# - - - -
def JP_C2(z80: Z80) -> int:
    if z80.Fz:
        return 12
    else:
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 16

# 0xC3 : JP a16
# - - - -
def JP_C3(z80: Z80) -> int:
    z80.PC = (z80.args[1] << 8) | z80.args[0]
    return 16

# 0xC4 : CALL NZ, a16
# - - - -
def CALL_C4(z80: Z80) -> int:
    if z80.Fz:
        return 12
    else:
        z80.push(z80.PC >> 8) # high addr
        z80.push(z80.PC & 0xFF) # low addr
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 24

# 0xC5 : PUSH BC
# - - - -
def PUSH_C5(z80: Z80) -> int:
    z80.push(z80.B) # high
    z80.push(z80.C) # low
    return 16

# 0xC6 : ADD A, d8
# Z 0 H C
def ADD_C6(z80: Z80) -> int:
    val = z80.A + z80.args[0]
    flag = 0b00000000

    # set flag H to 1 if carry from bit 3
    flag |= (((z80.A & 0xF) + (z80.args[0] & 0xF)) > 0xF) << FLAG_H
    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xC7 : RST 00H
# - - - -
def RST_C7(z80: Z80) -> int:
    z80.push(z80.PC >> 8) # high
    z80.push(z80.PC & 0xFF) # low
    z80.PC = 0x0000
    return 16

# 0xC8 : RET Z
# - - - -
def RET_C8(z80: Z80) -> int:
    if z80.Fz:
        addrLo = z80.pop()
        addrHi = z80.pop()
        z80.PC = (addrHi << 8) | addrLo
        return 20
    else:
        return 8

# 0xC9 : RET
# - - - -
def RET_C9(z80: Z80) -> int:
    addrLo = z80.pop()
    addrHi = z80.pop()
    z80.PC = (addrHi << 8) | addrLo
    return 16

# 0xCA : JP Z, a16
# - - - -
def JP_CA(z80: Z80) -> int:
    if z80.Fz:
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 16
    else:
        return 12

# 0xCB : PREFIX CB
# - - - -
def PREFIX_CB(z80: Z80) -> int:
    # z80.PREFIX_CB = True
    return 4

# 0xCC : CALL Z, a16
# - - - -
def CALL_CC(z80: Z80) -> int:
    if z80.Fz:
        z80.push(z80.PC >> 8) # high
        z80.push(z80.PC & 0xFF) # low
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 24
    else:
        return 12

# 0xCD : CALL a16
# - - - -
def CALL_CD(z80: Z80) -> int:
    z80.push(z80.PC >> 8) # high
    z80.push(z80.PC & 0xFF) # low
    z80.PC = (z80.args[1] << 8) | z80.args[0]
    return 24

# 0xCE : ADC A, d8
# Z 0 H C
def ADC_CE(z80: Z80) -> int:
    val = z80.A + z80.args[0] + z80.Fc
    flag = 0b00000000

    # set flag H to 1 if carry from bit 3
    flag |= (((z80.A & 0xF) + (z80.args[0] & 0xF) + z80.Fc) > 0xF) << FLAG_H
    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= (val & 0xFF == 0) << FLAG_Z

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xCF : RST 08H
# - - - -
def RST_CF(z80: Z80) -> int:
    z80.push(z80.PC >> 8) # high
    z80.push(z80.PC & 0xFF) # low
    z80.PC = 0x0008
    return 16

# 0xD0 : RET NC
# - - - -
def RET_D0(z80: Z80) -> int:
    if z80.Fc:
        return 8
    else:
        addrLo = z80.pop()
        addrHi = z80.pop()
        z80.PC = (addrHi << 8) | addrLo
        return 20

# 0xD1 : POP DE
# - - - -
def POP_D1(z80: Z80) -> int:
    z80.E = z80.pop()
    z80.D = z80.pop()
    return 12

# 0xD2 : JP NC, a16
# - - - -
def JP_D2(z80: Z80) -> int:
    if z80.Fc:
        return 12
    else:
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 16

# 0xD3 : NULL

# 0xD4 : CALL NC, a16
# - - - -
def CALL_D4(z80: Z80) -> int:
    if z80.Fc:
        return 12
    else:
        z80.push(z80.PC >> 8)  # high addr
        z80.push(z80.PC & 0xFF)  # low addr
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 24

# 0xD5 : PUSH DE
# - - - -
def PUSH_D5(z80: Z80) -> int:
    z80.push(z80.D) # high
    z80.push(z80.E) # low
    return 16

# 0xD6 : SUB d8
# Z 1 H C
def SUB_D6(z80: Z80) -> int:
    val = z80.A - z80.args[0]
    flag = 0b01000000

    # set flag H to 1 if borrow from bit 4
    flag |= ((z80.A & 0xF) < (z80.args[0] & 0xF)) << FLAG_H
    # set flag C to 1 if borrow from bit 8
    flag |= (val < 0) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= (val & 0xFF == 0) << FLAG_Z

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xD7 : RST 10H
# - - - -
def RST_D7(z80: Z80) -> int:
    z80.push(z80.PC >> 8) # high
    z80.push(z80.PC & 0xFF) # low
    z80.PC = 0x0010
    return 16

# 0xD8 : RET C
# - - - -
def RET_D8(z80: Z80) -> int:
    if z80.Fc:
        addrLo = z80.pop()
        addrHi = z80.pop()
        z80.PC = (addrHi << 8) | addrLo
        return 20
    else:
        return 8

# 0xD9 : RETI
# - - - -
def RETI_D9(z80: Z80) -> int:
    addrLo = z80.pop()
    addrHi = z80.pop()
    z80.PC = (addrHi << 8) | addrLo
    z80.interruptable = True
    return 16

# 0xDA : JP C, a16
# - - - -
def JP_DA(z80: Z80) -> int:
    if z80.Fc:
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 16
    else:
        return 12

# 0xDB : NULL

# 0xDC : CALL C, a16
# - - - -
def CALL_DC(z80: Z80) -> int:
    if z80.Fc:
        z80.push(z80.PC >> 8) # high
        z80.push(z80.PC & 0xFF) # low
        z80.PC = (z80.args[1] << 8) | z80.args[0]
        return 24
    else:
        return 12

# 0xDD : NULL

# 0xDE : SBC A, d8
# Z 1 H C
def SBC_DE(z80: Z80) -> int:
    val = z80.A - z80.args[0] - z80.Fc
    flag = 0b01000000

    # set flag H to 1 if borrow from bit 4
    flag |= (((z80.A & 0xF) - (z80.args[0] & 0xF) - z80.Fc) < 0) << FLAG_H
    # set flag C to 1 if borrow from bit 8
    flag |= (val < 0) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= (val & 0xFF == 0) << FLAG_Z

    z80.A = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xDF : RST 18H
# - - - -
def RST_DF(z80: Z80) -> int:
    z80.push(z80.PC >> 8) # high
    z80.push(z80.PC & 0xFF) # low
    z80.PC = 0x0018
    return 16

# 0xE0 : LDH (a8), A
# - - - -
def LDH_E0(z80: Z80) -> int:
    z80.emu.write(0xFF00 + z80.args[0], z80.A)
    return 12

# 0xE1 : POP HL
# - - - -
def POP_E1(z80: Z80) -> int:
    z80.L = z80.pop()
    z80.H = z80.pop()
    return 12

# 0xE2 : LD (C), A
# - - - -
def LD_E2(z80: Z80) -> int:
    z80.emu.write(0xFF00 + z80.C, z80.A)
    return 8

# 0xE3 : NULL

# 0xE4 : NULL

# 0xE5 : PUSH HL
# - - - -
def PUSH_E5(z80: Z80) -> int:
    z80.push(z80.H)  # high
    z80.push(z80.L)  # low
    return 16

# 0xE6 : AND d8
# Z 0 1 0
def AND_E6(z80: Z80) -> int:
    val = (z80.A & z80.args[0]) & 0xFF
    flag = 0b00100000

    # set flag Z to 1 if results 0
    flag |= (val == 0) << FLAG_Z

    z80.A = val
    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xE7 : RST 20H
# - - - -
def RST_E7(z80: Z80) -> int:
    z80.push(z80.PC >> 8)  # high
    z80.push(z80.PC & 0xFF)  # low
    z80.PC = 0x0020
    return 16

# 0xE8 : ADD SP, r8
# 0 0 H C
def ADD_E8(z80: Z80) -> int:
    val = z80.SP + z80.args[0]
    # 1 at msb (-)
    if z80.args[0] & 0x80:
        val -= 0x100
    flag = 0b00000000

    # set flag H to 1 if carry from bit 3
    flag |= (((z80.SP & 0x0F) + (z80.args[0] & 0x0F)) > 0x0F) << FLAG_H
    # set flag C to 1 if carry from bit 7
    flag |= (((z80.SP & 0xFF) + (z80.args[0] & 0xFF)) > 0xFF) << FLAG_C

    z80.SP = val & 0xFFFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 16

# 0xE9 : JP HL
# - - - -
def JP_E9(z80: Z80) -> int:
    z80.PC = (z80.H << 8) | z80.L
    return 4

# 0xEA : LD (a16), A
# - - - -
def LD_EA(z80: Z80) -> int:
    z80.emu.write((z80.args[1] << 8) | z80.args[0], z80.A)
    return 16

# 0xEB : NULL

# 0xEC : NULL

# 0xED : NULL

# 0xEE : XOR d8
# Z 0 0 0
def XOR_EE(z80: Z80) -> int:
    val = (z80.A ^ z80.args[0]) & 0xFF
    flag = 0b00000000

    # set flag Z to 1 if results 0
    flag |= (val == 0) << FLAG_Z

    z80.A = val
    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xEF : RST 28H
# - - - -
def RST_EF(z80: Z80) -> int:
    z80.push(z80.PC >> 8) # high
    z80.push(z80.PC & 0xFF) # low
    z80.PC = 0x0028
    return 16

# 0xF0 : LDH A, (a8)
# - - - -
def LDH_F0(z80: Z80) -> int:
    z80.A = z80.emu.read(0xFF00 + z80.args[0])
    return 12

# 0xF1 : POP AF
# Z N H C
def POP_F1(z80: Z80) -> int:
    z80.F = z80.pop() & 0xF0
    z80.A = z80.pop()
    return 12

# 0xF2 : LD A, (C)
# - - - -
def LD_F2(z80: Z80) -> int:
    z80.A = z80.emu.read(0xFF00 + z80.C)
    return 8

# 0xF3 : DI
# - - - -
def DI_F3(z80: Z80) -> int:
    z80.interruptable = False
    return 4

# 0xF4 : NULL

# 0xF5 : PUSH AF
# - - - -
def PUSH_F5(z80: Z80) -> int:
    z80.push(z80.A) # high
    z80.push(z80.F) # low
    return 16

# 0xF6 : OR d8
# Z 0 0 0
def OR_F6(z80: Z80) -> int:
    val = (z80.A | z80.args[0]) & 0xFF
    flag = 0b00000000

    # set flag Z to 1 if results 0
    flag |= (val == 0) << FLAG_Z

    z80.A = val
    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xF7 : RST 30H
# - - - -
def RST_F7(z80: Z80) -> int:
    z80.push(z80.PC >> 8)  # high
    z80.push(z80.PC & 0xFF)  # low
    z80.PC = 0x0030
    return 16

# 0xF8 : LD HL, SP + r8
# 0 0 H C
def LD_F8(z80: Z80) -> int:
    val = z80.SP + z80.args[0]
    # 1 at msb (-)
    if z80.args[0] & 0x80:
        val -= 0x100
    flag = 0b00000000

    # set flag H to 1 if carry from bit 3
    flag |= (((z80.SP & 0x0F) + (z80.args[0] & 0x0F)) > 0x0F) << FLAG_H
    # set flag C to 1 if carry from bit 7
    flag |= (((z80.SP & 0xFF) + (z80.args[0] & 0xFF)) > 0xFF) << FLAG_C

    z80.H = (val & 0xFF00) >> 8
    z80.L = val & 0xFF
    z80.F &= 0b00000000
    z80.F |= flag
    return 12

# 0xF9 : LD SP, HL
# - - - -
def LD_F9(z80: Z80) -> int:
    z80.SP = (z80.H << 8) | z80.L
    return 8

# 0xFA : LD A, (a16)
# - - - -
def LD_FA(z80: Z80) -> int:
    z80.A = z80.emu.read((z80.args[1] << 8) | z80.args[0])
    return 16

# 0xFB : EI
# - - - -
def EI_FB(z80: Z80) -> int:
    z80.interruptable = True
    return 4

# 0xFC : NULL

# 0xFD : NULL

# 0xFE : CP d8
# Z 1 H C
def CP_FE(z80: Z80) -> int:
    val = z80.A - z80.args[0]
    flag = 0b01000000

    # set flag H to 1 if borrow from bit 4
    flag |= ((z80.A & 0xF) < (z80.args[0] & 0xF)) << FLAG_H
    # set flag C to 1 if borrow from bit 8
    flag |= (val < 0) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return 8

# 0xFF : RST 38H
# - - - -
def RST_FF(z80: Z80) -> int:
    z80.push(z80.PC >> 8) # high
    z80.push(z80.PC & 0xFF) # low
    z80.PC = 0x0038
    return 16

###########################
# op codes with prefix CB #
###########################

def RLC_inner(z80: Z80, val: int) -> int:
    val = (val << 1) | (val >> 7)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x100 : RLC B
# Z 0 0 C
def RLC_100(z80: Z80) -> int:
    z80.B = RLC_inner(z80, z80.B)
    return 8

# 0x101 : RLC C
# Z 0 0 C
def RLC_101(z80: Z80) -> int:
    z80.C = RLC_inner(z80, z80.C)
    return 8

# 0x102 : RLC D
# Z 0 0 C
def RLC_102(z80: Z80) -> int:
    z80.D = RLC_inner(z80, z80.D)
    return 8

# 0x103 : RLC E
# Z 0 0 C
def RLC_103(z80: Z80) -> int:
    z80.E = RLC_inner(z80, z80.E)
    return 8

# 0x104 : RLC H
# Z 0 0 C
def RLC_104(z80: Z80) -> int:
    z80.H = RLC_inner(z80, z80.H)
    return 8

# 0x105 : RLC L
# Z 0 0 C
def RLC_105(z80: Z80) -> int:
    z80.L = RLC_inner(z80, z80.L)
    return 8

# 0x106 : RLC (HL)
# Z 0 0 C
def RLC_106(z80: Z80) -> int:
    z80.emu.write(z80.HL, RLC_inner(z80, z80.emu.read((z80.HL))))
    return 16

# 0x107 : RLC A
# Z 0 0 C
def RLC_107(z80: Z80) -> int:
    z80.A = RLC_inner(z80, z80.A)
    return 8

def RRC_inner(z80: Z80, val: int) -> int:
    val = (val >> 1) | ((val & 1) << 7) | ((val & 1) << 8)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x108 : RRC B
# Z 0 0 C
def RRC_108(z80: Z80) -> int:
    z80.B = RRC_inner(z80, z80.B)
    return 8

# 0x109 : RRC C
# Z 0 0 C
def RRC_109(z80: Z80) -> int:
    z80.C = RRC_inner(z80, z80.C)
    return 8

# 0x10A : RRC D
# Z 0 0 C
def RRC_10A(z80: Z80) -> int:
    z80.D = RRC_inner(z80, z80.D)
    return 8

# 0x10B : RRC E
# Z 0 0 C
def RRC_10B(z80: Z80) -> int:
    z80.E = RRC_inner(z80, z80.E)
    return 8

# 0x10C : RRC H
# Z 0 0 C
def RRC_10C(z80: Z80) -> int:
    z80.H = RRC_inner(z80, z80.H)
    return 8

# 0x10D : RRC L
# Z 0 0 C
def RRC_10D(z80: Z80) -> int:
    z80.L = RRC_inner(z80, z80.L)
    return 8

# 0x10E : RRC (HL)
# Z 0 0 C
def RRC_10E(z80: Z80) -> int:
    z80.emu.write(z80.HL, RRC_inner(z80, z80.emu.read(z80.HL)))
    return 16

# 0x10F : RRC A
# Z 0 0 C
def RRC_10F(z80: Z80) -> int:
    z80.A = RRC_inner(z80, z80.A)
    return 8

def RL_inner(z80: Z80, val: int) -> int:
    val = (val << 1) | z80.Fc
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x110 : RL B
# Z 0 0 C
def RL_110(z80: Z80) -> int:
    z80.B = RL_inner(z80, z80.B)
    return 8

# 0x111 : RL C
# Z 0 0 C
def RL_111(z80: Z80) -> int:
    z80.C = RL_inner(z80, z80.C)
    return 8

# 0x112 : RL D
# Z 0 0 C
def RL_112(z80: Z80) -> int:
    z80.D = RL_inner(z80, z80.D)
    return 8

# 0x113 : RL E
# Z 0 0 C
def RL_113(z80: Z80) -> int:
    z80.E = RL_inner(z80, z80.E)
    return 8

# 0x114 : RL H
# Z 0 0 C
def RL_114(z80: Z80) -> int:
    z80.H = RL_inner(z80, z80.H)
    return 8

# 0x115 : RL L
# Z 0 0 C
def RL_115(z80: Z80) -> int:
    z80.L = RL_inner(z80, z80.L)
    return 8

# 0x116 : RL (HL)
# Z 0 0 C
def RL_116(z80: Z80) -> int:
    z80.emu.write(z80.HL, RL_inner(z80, z80.emu.read((z80.HL))))
    return 16

# 0x117 : RL A
# Z 0 0 C
def RL_117(z80: Z80) -> int:
    z80.A = RL_inner(z80, z80.A)
    return 8

def RR_inner(z80: Z80, val: int) -> int:
    val = (val >> 1) | ((val & 1) << 8) | (z80.Fc << 7)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0x1

# 0x118 : RR B
# Z 0 0 C
def RR_118(z80: Z80) -> int:
    z80.B = RR_inner(z80, z80.B)
    return 8

# 0x119 : RR C
# Z 0 0 C
def RR_119(z80: Z80) -> int:
    z80.C = RR_inner(z80, z80.C)
    return 8

# 0x11A : RR D
# Z 0 0 C
def RR_11A(z80: Z80) -> int:
    z80.D = RR_inner(z80, z80.D)
    return 8

# 0x11B : RR E
# Z 0 0 C
def RR_11B(z80: Z80) -> int:
    z80.E = RR_inner(z80, z80.E)
    return 8

# 0x11C : RR H
# Z 0 0 C
def RR_11C(z80: Z80) -> int:
    z80.H = RR_inner(z80, z80.H)
    return 8

# 0x11D : RR L
# Z 0 0 C
def RR_11D(z80: Z80) -> int:
    z80.L = RR_inner(z80, z80.L)
    return 8

# 0x11E : RR (HL)
# Z 0 0 C
def RR_11E(z80: Z80) -> int:
    z80.emu.write(z80.HL, RR_inner(z80, z80.emu.read(z80.HL)))
    return 16

# 0x11F : RR A
# Z 0 0 C
def RR_11F(z80: Z80) -> int:
    z80.A = RR_inner(z80, z80.A)
    return 8

def SLA_inner(z80: Z80, val: int) -> int:
    val <<= 1
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x120 : SLA B
# Z 0 0 C
def SLA_120(z80: Z80) -> int:
    z80.B = SLA_inner(z80, z80.B)
    return 8

# 0x121 : SLA C
# Z 0 0 C
def SLA_121(z80: Z80) -> int:
    z80.C = SLA_inner(z80, z80.C)
    return 8

# 0x122 : SLA D
# Z 0 0 C
def SLA_122(z80: Z80) -> int:
    z80.D = SLA_inner(z80, z80.D)
    return 8

# 0x123 : SLA E
# Z 0 0 C
def SLA_123(z80: Z80) -> int:
    z80.E = SLA_inner(z80, z80.E)
    return 8

# 0x124 : SLA H
# Z 0 0 C
def SLA_124(z80: Z80) -> int:
    z80.H = SLA_inner(z80, z80.H)
    return 8

# 0x125 : SLA L
# Z 0 0 C
def SLA_125(z80: Z80) -> int:
    z80.L = SLA_inner(z80, z80.L)
    return 8

# 0x126 : SLA (HL)
# Z 0 0 C
def SLA_126(z80: Z80) -> int:
    z80.emu.write(z80.HL, SLA_inner(z80, z80.emu.read((z80.HL))))
    return 16

# 0x127 : SLA A
# Z 0 0 C
def SLA_127(z80: Z80) -> int:
    z80.A = SLA_inner(z80, z80.A)
    return 8

def SRA_inner(z80: Z80, val: int) -> int:
    val = (val >> 1) | (val & 0x80) | ((val & 1) << 8)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x128 : SRA B
# Z 0 0 C
def SRA_128(z80: Z80) -> int:
    z80.B = SRA_inner(z80, z80.B)
    return 8

# 0x129 : SRA C
# Z 0 0 C
def SRA_129(z80: Z80) -> int:
    z80.C = SRA_inner(z80, z80.C)
    return 8

# 0x12A : SRA D
# Z 0 0 C
def SRA_12A(z80: Z80) -> int:
    z80.D = SRA_inner(z80, z80.D)
    return 8

# 0x12B : SRA E
# Z 0 0 C
def SRA_12B(z80: Z80) -> int:
    z80.E = SRA_inner(z80, z80.E)
    return 8

# 0x12C : SRA H
# Z 0 0 C
def SRA_12C(z80: Z80) -> int:
    z80.H = SRA_inner(z80, z80.H)
    return 8

# 0x12D : SRA L
# Z 0 0 C
def SRA_12D(z80: Z80) -> int:
    z80.L = SRA_inner(z80, z80.L)
    return 8

# 0x12E : SRA (HL)
# Z 0 0 C
def SRA_12E(z80: Z80) -> int:
    z80.emu.write(z80.HL, SRA_inner(z80, z80.emu.read(z80.HL)))
    return 16

# 0x12F : SRA A
# Z 0 0 C
def SRA_12F(z80: Z80) -> int:
    z80.A = SRA_inner(z80, z80.A)
    return 8

def SWAP_inner(z80: Z80, val: int) -> int:
    val = ((val & 0xF0) >> 4) | ((val & 0x0F) << 4)
    flag = 0b00000000

    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x130 : SWAP B
# Z 0 0 0
def SWAP_130(z80: Z80) -> int:
    z80.B = SWAP_inner(z80, z80.B)
    return 8

# 0x131 : SWAP C
# Z 0 0 0
def SWAP_131(z80: Z80) -> int:
    z80.C = SWAP_inner(z80, z80.C)
    return 8

# 0x132 : SWAP D
# Z 0 0 0
def SWAP_132(z80: Z80) -> int:
    z80.D = SWAP_inner(z80, z80.D)
    return 8

# 0x133 : SWAP E
# Z 0 0 0
def SWAP_133(z80: Z80) -> int:
    z80.E = SWAP_inner(z80, z80.E)
    return 8

# 0x134 : SWAP H
# Z 0 0 0
def SWAP_134(z80: Z80) -> int:
    z80.H = SWAP_inner(z80, z80.H)
    return 8

# 0x135 : SWAP L
# Z 0 0 0
def SWAP_135(z80: Z80) -> int:
    z80.L = SWAP_inner(z80, z80.L)
    return 8

# 0x136 : SWAP (HL)
# Z 0 0 0
def SWAP_136(z80: Z80) -> int:
    z80.emu.write(z80.HL, SWAP_inner(z80, z80.emu.read((z80.HL))))
    return 16

# 0x137 : SWAP A
# Z 0 0 0
def SWAP_137(z80: Z80) -> int:
    z80.A = SWAP_inner(z80, z80.A)
    return 8

def SRL_inner(z80: Z80, val: int) -> int:
    val = (val >> 1) | ((val & 1) << 8)
    flag = 0b00000000

    # set flag C to 1 if carry from bit 7
    flag |= (val > 0xFF) << FLAG_C
    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00000000
    z80.F |= flag
    return val & 0xFF

# 0x138 : SRL B
# Z 0 0 C
def SRL_138(z80: Z80) -> int:
    z80.B = SRL_inner(z80, z80.B)
    return 8

# 0x139 : SRL C
# Z 0 0 C
def SRL_139(z80: Z80) -> int:
    z80.C = SRL_inner(z80, z80.C)
    return 8

# 0x13A : SRL D
# Z 0 0 C
def SRL_13A(z80: Z80) -> int:
    z80.D = SRL_inner(z80, z80.D)
    return 8

# 0x13B : SRL E
# Z 0 0 C
def SRL_13B(z80: Z80) -> int:
    z80.E = SRL_inner(z80, z80.E)
    return 8

# 0x13C : SRL H
# Z 0 0 C
def SRL_13C(z80: Z80) -> int:
    z80.H = SRL_inner(z80, z80.H)
    return 8

# 0x13D : SRL L
# Z 0 0 C
def SRL_13D(z80: Z80) -> int:
    z80.L = SRL_inner(z80, z80.L)
    return 8

# 0x13E : SRL (HL)
# Z 0 0 C
def SRL_13E(z80: Z80) -> int:
    z80.emu.write(z80.HL, SRL_inner(z80, z80.emu.read(z80.HL)))
    return 16

# 0x13F : SRL A
# Z 0 0 C
def SRL_13F(z80: Z80) -> int:
    z80.A = SRL_inner(z80, z80.A)
    return 8

def BIT_inner(z80: Z80, offset: int, val: int) -> None:
    val &= (1 << offset)
    flag = 0b00100000

    # set flag Z to 1 if results 0
    flag |= ((val & 0xFF) == 0) << FLAG_Z

    z80.F &= 0b00010000
    z80.F |= flag

# 0x140 : BIT 0, B
# Z 0 1 -
def BIT_140(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.B)
    return 8

# 0x141 : BIT 0, C
# Z 0 1 -
def BIT_141(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.C)
    return 8

# 0x142 : BIT 0, D
# Z 0 1 -
def BIT_142(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.D)
    return 8

# 0x143 : BIT 0, E
# Z 0 1 -
def BIT_143(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.E)
    return 8

# 0x144 : BIT 0, H
# Z 0 1 -
def BIT_144(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.H)
    return 8

# 0x145 : BIT 0, L
# Z 0 1 -
def BIT_145(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.L)
    return 8

# 0x146 : BIT 0, (HL)
# Z 0 1 -
def BIT_146(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.emu.read(z80.HL))
    return 12

# 0x147 : BIT 0, A
# Z 0 1 -
def BIT_147(z80: Z80) -> int:
    BIT_inner(z80, 0, z80.A)
    return 8

# 0x148 : BIT 1, B
# Z 0 1 -
def BIT_148(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.B)
    return 8

# 0x149 : BIT 1, C
# Z 0 1 -
def BIT_149(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.C)
    return 8

# 0x14A : BIT 1, D
# Z 0 1 -
def BIT_14A(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.D)
    return 8

# 0x14B : BIT 1, E
# Z 0 1 -
def BIT_14B(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.E)
    return 8

# 0x14C : BIT 1, H
# Z 0 1 -
def BIT_14C(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.H)
    return 8

# 0x14D : BIT 1, L
# Z 0 1 -
def BIT_14D(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.L)
    return 8

# 0x14E : BIT 1, (HL)
# Z 0 1 -
def BIT_14E(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.emu.read(z80.HL))
    return 12

# 0x14F : BIT 1, A
# Z 0 1 -
def BIT_14F(z80: Z80) -> int:
    BIT_inner(z80, 1, z80.A)
    return 8

# 0x150 : BIT 2, B
# Z 0 1 -
def BIT_150(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.B)
    return 8

# 0x151 : BIT 2, C
# Z 0 1 -
def BIT_151(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.C)
    return 8

# 0x152 : BIT 2, D
# Z 0 1 -
def BIT_152(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.D)
    return 8

# 0x153 : BIT 2, E
# Z 0 1 -
def BIT_153(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.E)
    return 8

# 0x154 : BIT 2, H
# Z 0 1 -
def BIT_154(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.H)
    return 8

# 0x155 : BIT 2, L
# Z 0 1 -
def BIT_155(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.L)
    return 8

# 0x156 : BIT 2, (HL)
# Z 0 1 -
def BIT_156(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.emu.read(z80.HL))
    return 12

# 0x157 : BIT 2, A
# Z 0 1 -
def BIT_157(z80: Z80) -> int:
    BIT_inner(z80, 2, z80.A)
    return 8

# 0x158 : BIT 3, B
# Z 0 1 -
def BIT_158(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.B)
    return 8

# 0x159 : BIT 3, C
# Z 0 1 -
def BIT_159(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.C)
    return 8

# 0x15A : BIT 3, D
# Z 0 1 -
def BIT_15A(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.D)
    return 8

# 0x15B : BIT 3, E
# Z 0 1 -
def BIT_15B(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.E)
    return 8

# 0x15C : BIT 3, H
# Z 0 1 -
def BIT_15C(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.H)
    return 8

# 0x15D : BIT 3, L
# Z 0 1 -
def BIT_15D(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.L)
    return 8

# 0x15E : BIT 3, (HL)
# Z 0 1 -
def BIT_15E(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.emu.read(z80.HL))
    return 12

# 0x15F : BIT 3, A
# Z 0 1 -
def BIT_15F(z80: Z80) -> int:
    BIT_inner(z80, 3, z80.A)
    return 8

# 0x160 : BIT 4, B
# Z 0 1 -
def BIT_160(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.B)
    return 8

# 0x161 : BIT 4, C
# Z 0 1 -
def BIT_161(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.C)
    return 8

# 0x162 : BIT 4, D
# Z 0 1 -
def BIT_162(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.D)
    return 8

# 0x163 : BIT 4, E
# Z 0 1 -
def BIT_163(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.E)
    return 8

# 0x164 : BIT 4, H
# Z 0 1 -
def BIT_164(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.H)
    return 8

# 0x165 : BIT 4, L
# Z 0 1 -
def BIT_165(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.L)
    return 8

# 0x166 : BIT 4, (HL)
# Z 0 1 -
def BIT_166(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.emu.read(z80.HL))
    return 12

# 0x167 : BIT 4, A
# Z 0 1 -
def BIT_167(z80: Z80) -> int:
    BIT_inner(z80, 4, z80.A)
    return 8

# 0x168 : BIT 5, B
# Z 0 1 -
def BIT_168(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.B)
    return 8

# 0x169 : BIT 5, C
# Z 0 1 -
def BIT_169(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.C)
    return 8

# 0x16A : BIT 5, D
# Z 0 1 -
def BIT_16A(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.D)
    return 8

# 0x16B : BIT 5, E
# Z 0 1 -
def BIT_16B(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.E)
    return 8

# 0x16C : BIT 5, H
# Z 0 1 -
def BIT_16C(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.H)
    return 8

# 0x16D : BIT 5, L
# Z 0 1 -
def BIT_16D(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.L)
    return 8

# 0x16E : BIT 5, (HL)
# Z 0 1 -
def BIT_16E(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.emu.read(z80.HL))
    return 12

# 0x16F : BIT 5, A
# Z 0 1 -
def BIT_16F(z80: Z80) -> int:
    BIT_inner(z80, 5, z80.A)
    return 8

# 0x170 : BIT 6, B
# Z 0 1 -
def BIT_170(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.B)
    return 8

# 0x171 : BIT 6, C
# Z 0 1 -
def BIT_171(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.C)
    return 8

# 0x172 : BIT 6, D
# Z 0 1 -
def BIT_172(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.D)
    return 8

# 0x173 : BIT 6, E
# Z 0 1 -
def BIT_173(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.E)
    return 8

# 0x174 : BIT 6, H
# Z 0 1 -
def BIT_174(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.H)
    return 8

# 0x175 : BIT 6, L
# Z 0 1 -
def BIT_175(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.L)
    return 8

# 0x176 : BIT 6, (HL)
# Z 0 1 -
def BIT_176(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.emu.read(z80.HL))
    return 12

# 0x177 : BIT 6, A
# Z 0 1 -
def BIT_177(z80: Z80) -> int:
    BIT_inner(z80, 6, z80.A)
    return 8

# 0x178 : BIT 7, B
# Z 0 1 -
def BIT_178(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.B)
    return 8

# 0x179 : BIT 7, C
# Z 0 1 -
def BIT_179(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.C)
    return 8

# 0x17A : BIT 7, D
# Z 0 1 -
def BIT_17A(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.D)
    return 8

# 0x17B : BIT 7, E
# Z 0 1 -
def BIT_17B(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.E)
    return 8

# 0x17C : BIT 7, H
# Z 0 1 -
def BIT_17C(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.H)
    return 8

# 0x17D : BIT 7, L
# Z 0 1 -
def BIT_17D(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.L)
    return 8

# 0x17E : BIT 7, (HL)
# Z 0 1 -
def BIT_17E(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.emu.read(z80.HL))
    return 12

# 0x17F : BIT 7, A
# Z 0 1 -
def BIT_17F(z80: Z80) -> int:
    BIT_inner(z80, 7, z80.A)
    return 8

# 0x180 : RES 0, B
# - - - -
def RES_180(z80: Z80) -> int:
    z80.B &= ~(1 << 0)
    return 8

# 0x181 : RES 0, C
# - - - -
def RES_181(z80: Z80) -> int:
    z80.C &= ~(1 << 0)
    return 8

# 0x182 : RES 0, D
# - - - -
def RES_182(z80: Z80) -> int:
    z80.D &= ~(1 << 0)
    return 8

# 0x183 : RES 0, E
# - - - -
def RES_183(z80: Z80) -> int:
    z80.E &= ~(1 << 0)
    return 8

# 0x184 : RES 0, H
# - - - -
def RES_184(z80: Z80) -> int:
    z80.H &= ~(1 << 0)
    return 8

# 0x185 : RES 0, L
# - - - -
def RES_185(z80: Z80) -> int:
    z80.L &= ~(1 << 0)
    return 8

# 0x186 : RES 0, (HL)
# - - - -
def RES_186(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 0)))
    return 16

# 0x187 : RES 0, A
# - - - -
def RES_187(z80: Z80) -> int:
    z80.A &= ~(1 << 0)
    return 8

# 0x188 : RES 1, B
# - - - -
def RES_188(z80: Z80) -> int:
    z80.B &= ~(1 << 1)
    return 8

# 0x189 : RES 1, C
# - - - -
def RES_189(z80: Z80) -> int:
    z80.C &= ~(1 << 1)
    return 8

# 0x18A : RES 1, D
# - - - -
def RES_18A(z80: Z80) -> int:
    z80.D &= ~(1 << 1)
    return 8

# 0x18B : RES 1, E
# - - - -
def RES_18B(z80: Z80) -> int:
    z80.E &= ~(1 << 1)
    return 8

# 0x18C : RES 1, H
# - - - -
def RES_18C(z80: Z80) -> int:
    z80.H &= ~(1 << 1)
    return 8

# 0x18D : RES 1, L
# - - - -
def RES_18D(z80: Z80) -> int:
    z80.L &= ~(1 << 1)
    return 8

# 0x18E : RES 1, (HL)
# - - - -
def RES_18E(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 1)))
    return 16

# 0x18F : RES 1, A
# - - - -
def RES_18F(z80: Z80) -> int:
    z80.A &= ~(1 << 1)
    return 8

# 0x190 : RES 2, B
# - - - -
def RES_190(z80: Z80) -> int:
    z80.B &= ~(1 << 2)
    return 8

# 0x191 : RES 2, C
# - - - -
def RES_191(z80: Z80) -> int:
    z80.C &= ~(1 << 2)
    return 8

# 0x192 : RES 2, D
# - - - -
def RES_192(z80: Z80) -> int:
    z80.D &= ~(1 << 2)
    return 8

# 0x193 : RES 2, E
# - - - -
def RES_193(z80: Z80) -> int:
    z80.E &= ~(1 << 2)
    return 8

# 0x194 : RES 2, H
# - - - -
def RES_194(z80: Z80) -> int:
    z80.H &= ~(1 << 2)
    return 8

# 0x195 : RES 2, L
# - - - -
def RES_195(z80: Z80) -> int:
    z80.L &= ~(1 << 2)
    return 8

# 0x196 : RES 2, (HL)
# - - - -
def RES_196(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 2)))
    return 16

# 0x197 : RES 2, A
# - - - -
def RES_197(z80: Z80) -> int:
    z80.A &= ~(1 << 2)
    return 8

# 0x198 : RES 3, B
# - - - -
def RES_198(z80: Z80) -> int:
    z80.B &= ~(1 << 3)
    return 8

# 0x199 : RES 3, C
# - - - -
def RES_199(z80: Z80) -> int:
    z80.C &= ~(1 << 3)
    return 8

# 0x19A : RES 3, D
# - - - -
def RES_19A(z80: Z80) -> int:
    z80.D &= ~(1 << 3)
    return 8

# 0x19B : RES 3, E
# - - - -
def RES_19B(z80: Z80) -> int:
    z80.E &= ~(1 << 3)
    return 8

# 0x19C : RES 3, H
# - - - -
def RES_19C(z80: Z80) -> int:
    z80.H &= ~(1 << 3)
    return 8

# 0x19D : RES 3, L
# - - - -
def RES_19D(z80: Z80) -> int:
    z80.L &= ~(1 << 3)
    return 8

# 0x19E : RES 3, (HL)
# - - - -
def RES_19E(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 3)))
    return 16

# 0x19F : RES 3, A
# - - - -
def RES_19F(z80: Z80) -> int:
    z80.A &= ~(1 << 3)
    return 8

# 0x1A0 : RES 4, B
# - - - -
def RES_1A0(z80: Z80) -> int:
    z80.B &= ~(1 << 4)
    return 8

# 0x1A1 : RES 4, C
# - - - -
def RES_1A1(z80: Z80) -> int:
    z80.C &= ~(1 << 4)
    return 8

# 0x1A2 : RES 4, D
# - - - -
def RES_1A2(z80: Z80) -> int:
    z80.D &= ~(1 << 4)
    return 8

# 0x1A3 : RES 4, E
# - - - -
def RES_1A3(z80: Z80) -> int:
    z80.E &= ~(1 << 4)
    return 8

# 0x1A4 : RES 4, H
# - - - -
def RES_1A4(z80: Z80) -> int:
    z80.H &= ~(1 << 4)
    return 8

# 0x1A5 : RES 4, L
# - - - -
def RES_1A5(z80: Z80) -> int:
    z80.L &= ~(1 << 4)
    return 8

# 0x1A6 : RES 4, (HL)
# - - - -
def RES_1A6(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 4)))
    return 16

# 0x1A7 : RES 4, A
# - - - -
def RES_1A7(z80: Z80) -> int:
    z80.A &= ~(1 << 4)
    return 8

# 0x1A8 : RES 5, B
# - - - -
def RES_1A8(z80: Z80) -> int:
    z80.B &= ~(1 << 5)
    return 8

# 0x1A9 : RES 5, C
# - - - -
def RES_1A9(z80: Z80) -> int:
    z80.C &= ~(1 << 5)
    return 8

# 0x1AA : RES 5, D
# - - - -
def RES_1AA(z80: Z80) -> int:
    z80.D &= ~(1 << 5)
    return 8

# 0x1AB : RES 5, E
# - - - -
def RES_1AB(z80: Z80) -> int:
    z80.E &= ~(1 << 5)
    return 8

# 0x1AC : RES 5, H
# - - - -
def RES_1AC(z80: Z80) -> int:
    z80.H &= ~(1 << 5)
    return 8

# 0x1AD : RES 5, L
# - - - -
def RES_1AD(z80: Z80) -> int:
    z80.L &= ~(1 << 5)
    return 8

# 0x1AE : RES 5, (HL)
# - - - -
def RES_1AE(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 5)))
    return 16

# 0x1AF : RES 5, A
# - - - -
def RES_1AF(z80: Z80) -> int:
    z80.A &= ~(1 << 5)
    return 8

# 0x1B0 : RES 6, B
# - - - -
def RES_1B0(z80: Z80) -> int:
    z80.B &= ~(1 << 6)
    return 8

# 0x1B1 : RES 6, C
# - - - -
def RES_1B1(z80: Z80) -> int:
    z80.C &= ~(1 << 6)
    return 8

# 0x1B2 : RES 6, D
# - - - -
def RES_1B2(z80: Z80) -> int:
    z80.D &= ~(1 << 6)
    return 8

# 0x1B3 : RES 6, E
# - - - -
def RES_1B3(z80: Z80) -> int:
    z80.E &= ~(1 << 6)
    return 8

# 0x1B4 : RES 6, H
# - - - -
def RES_1B4(z80: Z80) -> int:
    z80.H &= ~(1 << 6)
    return 8

# 0x1B5 : RES 6, L
# - - - -
def RES_1B5(z80: Z80) -> int:
    z80.L &= ~(1 << 6)
    return 8

# 0x1B6 : RES 6, (HL)
# - - - -
def RES_1B6(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 6)))
    return 16

# 0x1B7 : RES 6, A
# - - - -
def RES_1B7(z80: Z80) -> int:
    z80.A &= ~(1 << 6)
    return 8

# 0x1B8 : RES 7, B
# - - - -
def RES_1B8(z80: Z80) -> int:
    z80.B &= ~(1 << 7)
    return 8

# 0x1B9 : RES 7, C
# - - - -
def RES_1B9(z80: Z80) -> int:
    z80.C &= ~(1 << 7)
    return 8

# 0x1BA : RES 7, D
# - - - -
def RES_1BA(z80: Z80) -> int:
    z80.D &= ~(1 << 7)
    return 8

# 0x1BB : RES 7, E
# - - - -
def RES_1BB(z80: Z80) -> int:
    z80.E &= ~(1 << 7)
    return 8

# 0x1BC : RES 7, H
# - - - -
def RES_1BC(z80: Z80) -> int:
    z80.H &= ~(1 << 7)
    return 8

# 0x1BD : RES 7, L
# - - - -
def RES_1BD(z80: Z80) -> int:
    z80.L &= ~(1 << 7)
    return 8

# 0x1BE : RES 7, (HL)
# - - - -
def RES_1BE(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (~(1 << 7)))
    return 16

# 0x1BF : RES 7, A
# - - - -
def RES_1BF(z80: Z80) -> int:
    z80.A &= ~(1 << 7)
    return 8

# 0x1C0 : SET 0, B
# - - - -
def SET_1C0(z80: Z80) -> int:
    z80.B &= (1 << 0)
    return 8

# 0x1C1 : SET 0, C
# - - - -
def SET_1C1(z80: Z80) -> int:
    z80.C &= (1 << 0)
    return 8

# 0x1C2 : SET 0, D
# - - - -
def SET_1C2(z80: Z80) -> int:
    z80.D &= (1 << 0)
    return 8

# 0x1C3 : SET 0, E
# - - - -
def SET_1C3(z80: Z80) -> int:
    z80.E &= (1 << 0)
    return 8

# 0x1C4 : SET 0, H
# - - - -
def SET_1C4(z80: Z80) -> int:
    z80.H &= (1 << 0)
    return 8

# 0x1C5 : SET 0, L
# - - - -
def SET_1C5(z80: Z80) -> int:
    z80.L &= (1 << 0)
    return 8

# 0x1C6 : SET 0, (HL)
# - - - -
def SET_1C6(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 0))
    return 16

# 0x1C7 : SET 0, A
# - - - -
def SET_1C7(z80: Z80) -> int:
    z80.A &= (1 << 0)
    return 8

# 0x1C8 : SET 1, B
# - - - -
def SET_1C8(z80: Z80) -> int:
    z80.B &= (1 << 1)
    return 8

# 0x1C9 : SET 1, C
# - - - -
def SET_1C9(z80: Z80) -> int:
    z80.C &= (1 << 1)
    return 8

# 0x1CA : SET 1, D
# - - - -
def SET_1CA(z80: Z80) -> int:
    z80.D &= (1 << 1)
    return 8

# 0x1CB : SET 1, E
# - - - -
def SET_1CB(z80: Z80) -> int:
    z80.E &= (1 << 1)
    return 8

# 0x1CC : SET 1, H
# - - - -
def SET_1CC(z80: Z80) -> int:
    z80.H &= (1 << 1)
    return 8

# 0x1CD : SET 1, L
# - - - -
def SET_1CD(z80: Z80) -> int:
    z80.L &= (1 << 1)
    return 8

# 0x1CE : SET 1, (HL)
# - - - -
def SET_1CE(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 1))
    return 16

# 0x1CF : SET 1, A
# - - - -
def SET_1CF(z80: Z80) -> int:
    z80.A &= (1 << 1)
    return 8

# 0x1D0 : SET 2, B
# - - - -
def SET_1D0(z80: Z80) -> int:
    z80.B &= (1 << 2)
    return 8

# 0x1D1 : SET 2, C
# - - - -
def SET_1D1(z80: Z80) -> int:
    z80.C &= (1 << 2)
    return 8

# 0x1D2 : SET 2, D
# - - - -
def SET_1D2(z80: Z80) -> int:
    z80.D &= (1 << 2)
    return 8

# 0x1D3 : SET 2, E
# - - - -
def SET_1D3(z80: Z80) -> int:
    z80.E &= (1 << 2)
    return 8

# 0x1D4 : SET 2, H
# - - - -
def SET_1D4(z80: Z80) -> int:
    z80.H &= (1 << 2)
    return 8

# 0x1D5 : SET 2, L
# - - - -
def SET_1D5(z80: Z80) -> int:
    z80.L &= (1 << 2)
    return 8

# 0x1D6 : SET 2, (HL)
# - - - -
def SET_1D6(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 2))
    return 16

# 0x1D7 : SET 2, A
# - - - -
def SET_1D7(z80: Z80) -> int:
    z80.A &= (1 << 2)
    return 8

# 0x1D8 : SET 3, B
# - - - -
def SET_1D8(z80: Z80) -> int:
    z80.B &= (1 << 3)
    return 8

# 0x1D9 : SET 3, C
# - - - -
def SET_1D9(z80: Z80) -> int:
    z80.C &= (1 << 3)
    return 8

# 0x1DA : SET 3, D
# - - - -
def SET_1DA(z80: Z80) -> int:
    z80.D &= (1 << 3)
    return 8

# 0x1DB : SET 3, E
# - - - -
def SET_1DB(z80: Z80) -> int:
    z80.E &= (1 << 3)
    return 8

# 0x1DC : SET 3, H
# - - - -
def SET_1DC(z80: Z80) -> int:
    z80.H &= (1 << 3)
    return 8

# 0x1DD : SET 3, L
# - - - -
def SET_1DD(z80: Z80) -> int:
    z80.L &= (1 << 3)
    return 8

# 0x1DE : SET 3, (HL)
# - - - -
def SET_1DE(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 3))
    return 16

# 0x1DF : SET 3, A
# - - - -
def SET_1DF(z80: Z80) -> int:
    z80.A &= (1 << 3)
    return 8

# 0x1E0 : SET 4, B
# - - - -
def SET_1E0(z80: Z80) -> int:
    z80.B &= (1 << 4)
    return 8

# 0x1E1 : SET 4, C
# - - - -
def SET_1E1(z80: Z80) -> int:
    z80.C &= (1 << 4)
    return 8

# 0x1E2 : SET 4, D
# - - - -
def SET_1E2(z80: Z80) -> int:
    z80.D &= (1 << 4)
    return 8

# 0x1E3 : SET 4, E
# - - - -
def SET_1E3(z80: Z80) -> int:
    z80.E &= (1 << 4)
    return 8

# 0x1E4 : SET 4, H
# - - - -
def SET_1E4(z80: Z80) -> int:
    z80.H &= (1 << 4)
    return 8

# 0x1E5 : SET 4, L
# - - - -
def SET_1E5(z80: Z80) -> int:
    z80.L &= (1 << 4)
    return 8

# 0x1E6 : SET 4, (HL)
# - - - -
def SET_1E6(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 4))
    return 16

# 0x1E7 : SET 4, A
# - - - -
def SET_1E7(z80: Z80) -> int:
    z80.A &= (1 << 4)
    return 8

# 0x1E8 : SET 5, B
# - - - -
def SET_1E8(z80: Z80) -> int:
    z80.B &= (1 << 5)
    return 8

# 0x1E9 : SET 5, C
# - - - -
def SET_1E9(z80: Z80) -> int:
    z80.C &= (1 << 5)
    return 8

# 0x1EA : SET 5, D
# - - - -
def SET_1EA(z80: Z80) -> int:
    z80.D &= (1 << 5)
    return 8

# 0x1EB : SET 5, E
# - - - -
def SET_1EB(z80: Z80) -> int:
    z80.E &= (1 << 5)
    return 8

# 0x1EC : SET 5, H
# - - - -
def SET_1EC(z80: Z80) -> int:
    z80.H &= (1 << 5)
    return 8

# 0x1ED : SET 5, L
# - - - -
def SET_1ED(z80: Z80) -> int:
    z80.L &= (1 << 5)
    return 8

# 0x1EE : SET 5, (HL)
# - - - -
def SET_1EE(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 5))
    return 16

# 0x1EF : SET 5, A
# - - - -
def SET_1EF(z80: Z80) -> int:
    z80.A &= (1 << 5)
    return 8

# 0x1F0 : SET 6, B
# - - - -
def SET_1F0(z80: Z80) -> int:
    z80.B &= (1 << 6)
    return 8

# 0x1F1 : SET 6, C
# - - - -
def SET_1F1(z80: Z80) -> int:
    z80.C &= (1 << 6)
    return 8

# 0x1F2 : SET 6, D
# - - - -
def SET_1F2(z80: Z80) -> int:
    z80.D &= (1 << 6)
    return 8

# 0x1F3 : SET 6, E
# - - - -
def SET_1F3(z80: Z80) -> int:
    z80.E &= (1 << 6)
    return 8

# 0x1F4 : SET 6, H
# - - - -
def SET_1F4(z80: Z80) -> int:
    z80.H &= (1 << 6)
    return 8

# 0x1F5 : SET 6, L
# - - - -
def SET_1F5(z80: Z80) -> int:
    z80.L &= (1 << 6)
    return 8

# 0x1F6 : SET 6, (HL)
# - - - -
def SET_1F6(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 6))
    return 16

# 0x1F7 : SET 6, A
# - - - -
def SET_1F7(z80: Z80) -> int:
    z80.A &= (1 << 6)
    return 8

# 0x1F8 : SET 7, B
# - - - -
def SET_1F8(z80: Z80) -> int:
    z80.B &= (1 << 7)
    return 8

# 0x1F9 : SET 7, C
# - - - -
def SET_1F9(z80: Z80) -> int:
    z80.C &= (1 << 7)
    return 8

# 0x1FA : SET 7, D
# - - - -
def SET_1FA(z80: Z80) -> int:
    z80.D &= (1 << 7)
    return 8

# 0x1FB : SET 7, E
# - - - -
def SET_1FB(z80: Z80) -> int:
    z80.E &= (1 << 7)
    return 8

# 0x1FC : SET 7, H
# - - - -
def SET_1FC(z80: Z80) -> int:
    z80.H &= (1 << 7)
    return 8

# 0x1FD : SET 7, L
# - - - -
def SET_1FD(z80: Z80) -> int:
    z80.L &= (1 << 7)
    return 8

# 0x1FE : SET 7, (HL)
# - - - -
def SET_1FE(z80: Z80) -> int:
    z80.emu.write(z80.HL, z80.emu.read(z80.HL) & (1 << 7))
    return 16

# 0x1FF : SET 7, A
# - - - -
def SET_1FF(z80: Z80) -> int:
    z80.A &= (1 << 7)
    return 8
