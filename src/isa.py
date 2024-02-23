from __future__ import annotations

from enum import Enum


class Opcode(Enum):
    ADD = "add", 0x0
    SUB = "subtraction", 0x1
    DIV = "division", 0x2
    MOD = "division remainder", 0x3

    LOAD = "load", 0x4
    SAVE = "save", 0x5

    INPUT = "input", 0x6
    PRINT = "print", 0x7

    CALL = "call", 0x8
    RETURN = "return", 0x9
    PUSH = "push", 0xA
    POP = "pop", 0xB

    CMP = "compare", 0xC
    JMP = "jmp", 0xD
    JZ = "jz", 0xE

    HLT = "halt", 0xF

    def __str__(self):
        return str(self.value[0])

    def to_binary(self):
        return format(self.value[1], "X")


class AddressingType(Enum):
    DIRECT = "", 0x0
    INDIRECT = "$", 0x1
    OPERAND_LOAD = "#", 0x2
    SP_INDIRECT = "&", 0x3

    def __str__(self):
        return str(self.value[0])

    def to_binary(self):
        return format(self.value[1], "X")


def command_from_hex(hex_command: str) -> tuple[Opcode | None, AddressingType | None, int]:
    opcode = None
    addr_type = None
    arg = int(hex_command[2:], 16)

    for o in Opcode:
        if o.value[1] == int(hex_command[0], 16):
            opcode = o

    for at in AddressingType:
        if at.value[1] == int(hex_command[1], 16):
            addr_type = at

    return opcode, addr_type, arg


def hex_to_mnemonic(hex_command: str) -> str:
    opcode, addr_type, arg = command_from_hex(hex_command)
    mnemonic = str(opcode)

    if opcode not in {Opcode.PRINT, Opcode.INPUT, Opcode.RETURN, Opcode.PUSH, Opcode.POP, Opcode.HLT}:
        mnemonic += f" {addr_type}{arg}"

    return mnemonic


def command_to_hex(opcode: Opcode, addressing_type: AddressingType | None = None, operand: int | None = None) -> str:
    binary = opcode.to_binary()

    if addressing_type:
        binary += addressing_type.to_binary()
    else:
        binary = binary.ljust(2, "0")

    if operand is not None:
        binary += format(int(operand), "X").zfill(6)
    else:
        binary = binary.ljust(8, "0")

    return binary
