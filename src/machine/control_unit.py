from __future__ import annotations

from src.isa import command_from_hex, hex_to_mnemonic
from src.machine.data_path import (
    AccSelSignal,
    ArSelSignal,
    DataPath,
    IpSelSignal,
    LeftOperandSelSignal,
    MemAddrSelSignal,
    MemDataSelSignal,
    RightOperandSelSignal,
    SpSelSignal,
)
from src.translator.translator import AddressingType, Opcode


class ControlUnit:
    def __init__(self, data_path: DataPath):
        self.data_path = data_path
        self._tick = 0

    def tick(self):
        self._tick += 1

    def execute_control_flow_instruction(self, opcode, addr):
        if opcode is Opcode.HLT:
            raise StopIteration()

        if opcode is Opcode.JMP:
            self.data_path.latch_instr_ptr(IpSelSignal.CU, addr)
            self.tick()

        elif opcode is Opcode.JZ:
            if self.data_path.zero():
                self.data_path.latch_instr_ptr(IpSelSignal.CU, addr)
            else:
                self.data_path.latch_instr_ptr(IpSelSignal.INC)
            self.tick()

        elif opcode is Opcode.CALL:
            self.data_path.latch_instr_ptr(IpSelSignal.INC)
            self.data_path.latch_stack_ptr(SpSelSignal.DEC)
            self.tick()

            self.data_path.signal_wr(MemDataSelSignal.IP, MemAddrSelSignal.SP)
            self.data_path.latch_instr_ptr(IpSelSignal.CU, addr)
            self.tick()

        elif opcode is Opcode.RETURN:
            self.data_path.signal_alu_perform(LeftOperandSelSignal.NULL, RightOperandSelSignal.SP_MEM, Opcode.ADD)
            self.tick()

            self.data_path.latch_instr_ptr(IpSelSignal.ALU)
            self.data_path.latch_stack_ptr(SpSelSignal.INC)
            self.tick()

    def execute_alu_instruction(self, addr_type, opcode, arg):
        if addr_type is AddressingType.OPERAND_LOAD:
            self.data_path.signal_alu_perform(LeftOperandSelSignal.ACC, RightOperandSelSignal.CU, opcode, arg)
        else:
            self.process_address_selection(addr_type, arg)
            self.data_path.signal_alu_perform(LeftOperandSelSignal.ACC, RightOperandSelSignal.AR_MEM, opcode, arg)

        self.tick()

    def process_address_selection(self, addr_type: AddressingType, addr: int):
        if addr_type is AddressingType.DIRECT:
            self.data_path.latch_addr_reg(ArSelSignal.CU, addr)
            self.tick()

        elif addr_type is AddressingType.INDIRECT:
            self.data_path.latch_addr_reg(ArSelSignal.CU, addr)
            self.tick()

            self.data_path.signal_alu_perform(LeftOperandSelSignal.NULL, RightOperandSelSignal.AR_MEM, Opcode.ADD)
            self.tick()

            self.data_path.latch_addr_reg(ArSelSignal.ALU)
            self.tick()

        elif addr_type is AddressingType.SP_INDIRECT:
            self.data_path.signal_alu_perform(LeftOperandSelSignal.SP, RightOperandSelSignal.CU, Opcode.ADD, addr)
            self.tick()

            self.data_path.latch_addr_reg(ArSelSignal.ALU)
            self.tick()

    def decode_and_execute_instruction(self):
        instr = self.data_path.memory[self.data_path.ip]
        opcode, addr_type, arg = command_from_hex(instr)

        if opcode in {Opcode.JMP, Opcode.JZ, Opcode.CALL, Opcode.RETURN, Opcode.HLT}:
            self.execute_control_flow_instruction(opcode, arg)
            return

        if opcode in {Opcode.ADD, Opcode.SUB, Opcode.DIV, Opcode.MOD, Opcode.CMP}:
            self.execute_alu_instruction(addr_type, opcode, arg)

            if opcode is not Opcode.CMP:
                self.data_path.latch_acc(AccSelSignal.ALU)

        if opcode is Opcode.LOAD:
            if addr_type is AddressingType.OPERAND_LOAD:
                self.data_path.signal_alu_perform(LeftOperandSelSignal.NULL, RightOperandSelSignal.CU, Opcode.ADD, arg)
            else:
                self.process_address_selection(addr_type, arg)
                self.data_path.signal_alu_perform(LeftOperandSelSignal.NULL, RightOperandSelSignal.AR_MEM, Opcode.ADD)

            self.tick()
            self.data_path.latch_acc(AccSelSignal.ALU)

        if opcode is Opcode.SAVE:
            self.process_address_selection(addr_type, arg)
            self.data_path.signal_wr(MemDataSelSignal.ACC, MemAddrSelSignal.AR)

        if opcode is Opcode.PRINT:
            self.data_path.signal_output()

        if opcode is Opcode.INPUT:
            self.data_path.latch_acc(AccSelSignal.IN)

        if opcode is Opcode.PUSH:
            self.data_path.latch_stack_ptr(SpSelSignal.DEC)
            self.tick()

            self.data_path.signal_wr(MemDataSelSignal.ACC, MemAddrSelSignal.SP)

        if opcode is Opcode.POP:
            self.data_path.latch_stack_ptr(SpSelSignal.INC)

        self.data_path.latch_instr_ptr(IpSelSignal.INC)
        self.tick()

    def __repr__(self):
        state_repr = "TICK: {:4}, IP: {:4}, AR: {:4}, SP: {:4}, ALU: {:4}, ACC: {:4}".format(
            self._tick, self.data_path.ip, self.data_path.ar, self.data_path.sp, self.data_path.alu, self.data_path.acc
        )

        instr = self.data_path.memory[self.data_path.ip]
        instr_repr = hex_to_mnemonic(instr)

        return "{} \t{}".format(state_repr, instr_repr)
