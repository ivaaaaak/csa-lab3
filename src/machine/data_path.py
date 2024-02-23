from __future__ import annotations

import logging
from enum import Enum

from src.translator.translator import Opcode


class AccSelSignal(Enum):
    IN = 0
    ALU = 1


class ArSelSignal(Enum):
    ALU = 0
    CU = 1


class IpSelSignal(Enum):
    INC = 0
    CU = 1
    ALU = 2


class SpSelSignal(Enum):
    INC = 0
    DEC = 1


class MemDataSelSignal(Enum):
    ACC = 0
    IP = 1


class MemAddrSelSignal(Enum):
    SP = 0
    AR = 1


class LeftOperandSelSignal(Enum):
    NULL = 0
    ACC = 1
    SP = 2


class RightOperandSelSignal(Enum):
    NULL = 0
    AR_MEM = 1
    SP_MEM = 2
    CU = 3


class DataPath:
    def __init__(self, memory, input_buffer):
        self.memory_size = 2048
        self.memory = memory
        self.memory.extend(["00000000"] * (2048 - len(memory)))

        self.acc = 0
        self.sp = self.memory_size
        self.ip = 0
        self.ar = 0
        self.alu = 0

        self.input_buffer = input_buffer
        self.output_buffer = []

    def latch_acc(self, sel: AccSelSignal) -> None:
        if sel == AccSelSignal.ALU:
            self.acc = self.alu

        elif sel == AccSelSignal.IN:
            if len(self.input_buffer) == 0:
                raise EOFError()
            self.acc = ord(self.input_buffer.pop(0))

    def latch_addr_reg(self, sel: ArSelSignal, addr: int | None = None) -> None:
        if sel is ArSelSignal.ALU:
            self.ar = self.alu

        elif sel is ArSelSignal.CU:
            self.ar = addr

    def latch_instr_ptr(self, sel: IpSelSignal, addr: int | None = None) -> None:
        if sel == IpSelSignal.INC:
            self.ip += 1

        elif sel == IpSelSignal.CU:
            self.ip = addr

        elif sel == IpSelSignal.ALU:
            self.ip = self.alu

    def latch_stack_ptr(self, sel: SpSelSignal) -> None:
        if sel == SpSelSignal.INC:
            self.sp += 1

        elif sel == SpSelSignal.DEC:
            self.sp -= 1

    def signal_wr(self, data_sel: MemDataSelSignal, addr_sel: MemAddrSelSignal):
        addr = self.ar if addr_sel == MemAddrSelSignal.AR else self.sp

        if data_sel == MemDataSelSignal.ACC:
            self.memory[addr] = f"{self.acc:X}".zfill(8)

        elif data_sel == MemDataSelSignal.IP:
            self.memory[addr] = f"{self.ip:X}".zfill(8)

    def signal_output(self):
        symbol = chr(self.acc)
        logging.debug("output: %s << %s", repr("".join(self.output_buffer)), repr(symbol))
        self.output_buffer.append(symbol)

    def get_left_operand(self, sel: LeftOperandSelSignal) -> int:
        if sel is LeftOperandSelSignal.SP:
            return self.sp
        if sel is LeftOperandSelSignal.NULL:
            return 0
        if sel is LeftOperandSelSignal.ACC:
            return self.acc
        return -1

    def get_right_operand(self, sel: RightOperandSelSignal, operand: int = -1) -> int:
        if sel is RightOperandSelSignal.AR_MEM:
            return int(self.memory[self.ar], 16)
        if sel is RightOperandSelSignal.SP_MEM:
            return int(self.memory[self.sp], 16)
        if sel is RightOperandSelSignal.NULL:
            return 0
        if sel is RightOperandSelSignal.CU:
            return operand
        return -1

    def signal_alu_perform(
        self,
        left_operand_sel: LeftOperandSelSignal,
        right_operand_sel: RightOperandSelSignal,
        opcode: Opcode,
        operand: int = -1,
    ):
        left_operand = self.get_left_operand(left_operand_sel)
        right_operand = self.get_right_operand(right_operand_sel, operand)

        if opcode is Opcode.ADD:
            self.alu = left_operand + right_operand
        elif opcode is Opcode.SUB or opcode is Opcode.CMP:
            self.alu = left_operand - right_operand
        elif opcode is Opcode.DIV:
            self.alu = left_operand // right_operand
        elif opcode is Opcode.MOD:
            self.alu = left_operand % right_operand

    def zero(self):
        return self.alu == 0
