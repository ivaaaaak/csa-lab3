from __future__ import annotations

import re

from src.isa import AddressingType, Opcode, command_from_hex, command_to_hex
from src.translator.errors import TermError
from src.translator.lexer import arithmetic_symbols, boolean_literal, comparison_symbols


def arithmetic_symbol_to_opcode(symbol):
    return {
        "+": Opcode.ADD,
        "-": Opcode.SUB,
        "/": Opcode.DIV,
        "%": Opcode.MOD,
    }.get(symbol)


class Translator:
    def __init__(self):
        self.pc = 0

        self.code_memory = []
        self.data_memory = [""]

        self.variables = {}
        self.string_arrays = {}
        self.literals = {}

        self.functions = {}
        self.fun_variables = {}

    def add_command(
        self,
        opcode: Opcode | None = None,
        addressing_type: AddressingType | None = None,
        operand: int | None = None,
        index: int | None = None,
    ):
        if opcode is None:
            self.code_memory.append("")
            self.pc += 1

        elif index is None:
            self.code_memory.append(command_to_hex(opcode, addressing_type, operand))
            self.pc += 1
        else:
            self.code_memory[index] = command_to_hex(opcode, addressing_type, operand)

    def add_data(self, data: int, count: int = 1) -> int:
        new_data_addr = len(self.data_memory)
        self.data_memory.extend([format(data, "X").zfill(8)] * count)
        return new_data_addr

    def operation_with_var(self, term, opcode: Opcode, var_name: str, fun_name: str) -> None:
        var_addr = self.variables.get(var_name)

        if var_addr is not None:
            self.add_command(opcode, AddressingType.DIRECT, var_addr)

        elif fun_name is not None:
            try:
                var_addr = self.fun_variables.get(fun_name).index(var_name)
                self.add_command(opcode, AddressingType.SP_INDIRECT, var_addr)

            except ValueError:
                raise TermError(term, "No such variable") from ValueError
        else:
            raise TermError(term, "No such variable")

    def operation_with_num_literal(self, term, opcode: Opcode, num_literal: int) -> None:
        if num_literal <= pow(2, 24) - 1:
            self.add_command(opcode, AddressingType.OPERAND_LOAD, num_literal)

        elif num_literal <= pow(2, 32) - 1:
            addr = self.literals[num_literal]

            if addr is None:
                addr = self.add_data(num_literal)
                self.literals[num_literal] = addr

            self.add_command(opcode, AddressingType.DIRECT, addr)
        else:
            raise TermError(term, "Numbers more than (2^32 - 1) are not allowed")

    def operation_with_bool_literal(self, opcode: Opcode, bool_literal: str) -> None:
        if bool_literal == "T":
            self.add_command(opcode, AddressingType.OPERAND_LOAD, 1)
        else:
            self.add_command(opcode, AddressingType.OPERAND_LOAD, 0)

    def get_string_literal_addr(self, string_literal: str) -> int:
        addr = self.literals.get(string_literal)

        if addr is None:
            addr = len(self.data_memory)
            self.literals[string_literal] = addr

            for char in string_literal:
                self.add_data(ord(char))
            self.add_data(0)

        return addr

    def translate_fun(self, term):
        name = term[1]
        args_names = term[2]
        expressions = term[3:]

        jmp_command_pc = self.pc
        self.add_command()

        self.functions[name] = self.pc
        args_names.append("")
        self.fun_variables[name] = list(reversed(args_names))

        for expr in expressions:
            if isinstance(expr, list):
                self.translate_term(expr, name)
            else:
                self.operation_with_var(term, Opcode.LOAD, expr, name)

        for arg in self.fun_variables[name]:
            if arg != "":
                self.add_command(Opcode.POP)
            else:
                break

        self.add_command(Opcode.RETURN)
        self.add_command(Opcode.JMP, AddressingType.DIRECT, self.pc, jmp_command_pc)

    def translate_fun_call(self, term, fun_name):
        name = term[0]
        args = term[1:]

        for arg in args:
            if re.match(r"\d+", str(arg)):
                self.operation_with_num_literal(term, Opcode.LOAD, int(arg))

            elif isinstance(arg, list):
                self.translate_term(arg, fun_name)
            else:
                self.operation_with_var(term, Opcode.LOAD, arg, fun_name)

            self.add_command(Opcode.PUSH)

        fun_addr = self.functions.get(name)
        self.add_command(Opcode.CALL, AddressingType.DIRECT, fun_addr)

        for _ in args:
            self.add_command(Opcode.POP)

    def translate_action(self, term, action, fun_name):
        if isinstance(action, list):
            self.translate_term(action, fun_name)

        elif re.match(r"\d+", str(action)):
            self.operation_with_num_literal(term, Opcode.LOAD, int(action))

        elif re.match(r"'.*\n*'", str(action)):
            string_addr = self.get_string_literal_addr(str(action)[1:-1])
            self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, string_addr)

        elif str(action) in boolean_literal():
            self.operation_with_bool_literal(Opcode.LOAD, action)

        else:
            self.operation_with_var(term, Opcode.LOAD, action, fun_name)

    def translate_if(self, term, fun_name):
        condition = term[1]
        if_true = term[2]
        if_false = term[3] if len(term) == 4 else None

        if isinstance(condition, list):
            self.translate_term(condition, fun_name)

        elif str(condition) in boolean_literal():
            self.operation_with_bool_literal(Opcode.LOAD, condition)
        else:
            self.operation_with_var(term, Opcode.LOAD, condition, fun_name)

        jz_command_pc = self.pc
        self.add_command()

        self.translate_action(term, if_true, fun_name)

        if if_false is None:
            self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc, jz_command_pc)
            return

        jmp_command_pc = self.pc
        self.add_command()
        self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc, jz_command_pc)

        self.translate_action(term, if_false, fun_name)
        self.add_command(Opcode.JMP, AddressingType.DIRECT, self.pc, jmp_command_pc)

    def translate_while(self, term, fun_name):
        condition = term[1]
        actions = term[2:]

        condition_pc = self.pc

        if isinstance(condition, list):
            self.translate_term(condition, fun_name)
        else:
            self.operation_with_var(term, Opcode.LOAD, condition, fun_name)

        jz_command_pc = self.pc
        self.add_command()

        for act in actions:
            if isinstance(act, list):
                self.translate_term(act, fun_name)

            elif re.match(r"\d+", str(act)):
                self.operation_with_num_literal(term, Opcode.LOAD, int(act))

            elif str(act) in boolean_literal():
                self.operation_with_bool_literal(Opcode.LOAD, act)

            else:
                self.operation_with_var(term, Opcode.LOAD, act, fun_name)

        self.add_command(Opcode.JMP, AddressingType.DIRECT, condition_pc)
        self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc, jz_command_pc)

    def get_var_address(self, var_name, fun_name):
        var_addr = self.variables.get(var_name)

        if var_addr is None and fun_name is not None:
            try:
                var_addr = self.fun_variables.get(fun_name).index(var_name)
            except ValueError:
                var_addr = None

        if var_addr is None:
            if fun_name is not None:
                self.fun_variables.get(fun_name).insert(0, var_name)
                self.add_command(Opcode.PUSH)
                return var_addr, True

            var_addr = self.add_data(0)
            self.variables[var_name] = var_addr

        return var_addr, False

    def translate_set(self, term, fun_name):
        var_name = term[1]
        var_value = term[2]

        if isinstance(var_value, list):
            self.translate_term(var_value, fun_name)

        elif re.match(r"\d+", str(var_value)):
            self.operation_with_num_literal(term, Opcode.LOAD, int(var_value))

        elif str(var_value) in boolean_literal():
            self.operation_with_bool_literal(Opcode.LOAD, var_value)
        else:
            self.operation_with_var(term, Opcode.LOAD, var_value, fun_name)

        var_addr, is_pushed = self.get_var_address(var_name, fun_name)

        if fun_name is not None:
            if not is_pushed:
                self.add_command(Opcode.SAVE, AddressingType.SP_INDIRECT, var_addr)
        else:
            self.add_command(Opcode.SAVE, AddressingType.DIRECT, var_addr)

    def translate_set_char(self, term, fun_name):
        string_name = term[1]
        pos = term[2]
        char = term[3]

        string_info = self.string_arrays.get(string_name)

        if string_info is None:
            raise TermError(term, "No such string name")

        string_addr = string_info[0]
        new_char_addr = self.add_data(0)

        self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, string_addr)

        if re.match(r"\d+", str(pos)):
            self.operation_with_num_literal(term, Opcode.ADD, int(pos))
        else:
            self.operation_with_var(term, Opcode.ADD, pos, fun_name)

        self.add_command(Opcode.SAVE, AddressingType.DIRECT, new_char_addr)

        if isinstance(char, list):
            self.translate_term(char, fun_name)
        elif re.match(r"\d+", str(char)):
            self.operation_with_num_literal(term, Opcode.LOAD, int(char))
        else:
            self.operation_with_var(term, Opcode.LOAD, char, fun_name)

        self.add_command(Opcode.SAVE, AddressingType.INDIRECT, new_char_addr)

    def translate_print_string(self, term):
        string = term[1]

        string_addr_addr = self.add_data(0)

        if re.match(r"'.*\n*'", str(string)):
            string_addr = self.get_string_literal_addr(string[1:-1])
            self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, string_addr)

        elif isinstance(string, list):
            self.translate_term(string)

        else:
            string_info = self.string_arrays.get(string)

            if string_info is None:
                raise TermError(term, "No such string name")

            string_addr = string_info[0]
            self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, string_addr)

        self.add_command(Opcode.SAVE, AddressingType.DIRECT, string_addr_addr)

        self.add_command(Opcode.LOAD, AddressingType.INDIRECT, string_addr_addr)
        self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc + 6)
        self.add_command(Opcode.PRINT)

        self.add_command(Opcode.LOAD, AddressingType.DIRECT, string_addr_addr)
        self.add_command(Opcode.ADD, AddressingType.OPERAND_LOAD, 1)
        self.add_command(Opcode.SAVE, AddressingType.DIRECT, string_addr_addr)

        self.add_command(Opcode.JMP, AddressingType.DIRECT, self.pc - 6)

    def translate_print_int(self, term, fun_name):
        arg = term[1]

        array_addr = self.string_arrays.get("print-int")

        if array_addr is None:
            array_addr = self.add_data(0, 11)
            self.string_arrays["print-int"] = (array_addr, 11)
            self.add_data(array_addr + 1)

        array_start = array_addr + 11

        if isinstance(arg, list):
            self.translate_term(arg)
        elif re.match(r"\d+", str(arg)):
            self.operation_with_num_literal(term, Opcode.LOAD, arg)
        else:
            self.operation_with_var(term, Opcode.LOAD, arg, fun_name)

        self.add_command(Opcode.PUSH)

        start_pc = self.pc

        self.add_command(Opcode.LOAD, AddressingType.SP_INDIRECT, 0)
        self.add_command(Opcode.MOD, AddressingType.OPERAND_LOAD, 10)
        self.add_command(Opcode.ADD, AddressingType.OPERAND_LOAD, ord("0"))
        self.add_command(Opcode.SAVE, AddressingType.INDIRECT, array_start)

        self.add_command(Opcode.LOAD, AddressingType.SP_INDIRECT, 0)
        self.add_command(Opcode.DIV, AddressingType.OPERAND_LOAD, 10)
        self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc + 6)
        self.add_command(Opcode.SAVE, AddressingType.SP_INDIRECT, 0)

        self.add_command(Opcode.LOAD, AddressingType.DIRECT, array_start)
        self.add_command(Opcode.ADD, AddressingType.OPERAND_LOAD, 1)
        self.add_command(Opcode.SAVE, AddressingType.DIRECT, array_start)

        self.add_command(Opcode.JMP, AddressingType.DIRECT, start_pc)
        self.add_command(Opcode.POP)

        start_pc = self.pc

        self.add_command(Opcode.LOAD, AddressingType.INDIRECT, array_start)
        self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc + 6)
        self.add_command(Opcode.PRINT)

        self.add_command(Opcode.LOAD, AddressingType.DIRECT, array_start)
        self.add_command(Opcode.SUB, AddressingType.OPERAND_LOAD, 1)
        self.add_command(Opcode.SAVE, AddressingType.DIRECT, array_start)

        self.add_command(Opcode.JMP, AddressingType.DIRECT, start_pc)

        self.add_command(Opcode.LOAD, AddressingType.DIRECT, array_start)
        self.add_command(Opcode.ADD, AddressingType.OPERAND_LOAD, 1)
        self.add_command(Opcode.SAVE, AddressingType.DIRECT, array_start)

    def translate_print_char(self, term, fun_name):
        arg = term[1]

        if isinstance(arg, list):
            self.translate_term(arg, fun_name)

        elif re.match(r"\d+", str(arg)):
            self.operation_with_num_literal(term, Opcode.LOAD, arg)
        else:
            self.operation_with_var(term, Opcode.LOAD, arg, fun_name)

        self.add_command(Opcode.PRINT)

    def translate_read_char(self):
        self.add_command(Opcode.INPUT)

    def translate_alloc(self, term):
        string_name = term[1]
        string_size = int(term[2]) + 1

        if re.match(r"\d+", str(string_size)):
            string_addr = self.add_data(0, string_size)
        else:
            raise TermError(term, "String size must be a number")

        self.string_arrays[string_name] = (string_addr, string_size)

    def translate_comparison_symbol(self, term, fun_name):
        arg1 = term[1]
        arg2 = term[2]

        if re.match(r"\d+", str(arg1)):
            self.operation_with_num_literal(term, Opcode.LOAD, int(arg1))

        elif isinstance(arg1, list):
            self.translate_term(arg1, fun_name)
        else:
            self.operation_with_var(term, Opcode.LOAD, arg1, fun_name)

        if re.match(r"\d+", str(arg2)):
            self.operation_with_num_literal(term, Opcode.CMP, int(arg2))

        elif isinstance(arg1, list):
            self.translate_term(arg2, fun_name)
        else:
            self.operation_with_var(term, Opcode.CMP, arg2, fun_name)

        arg_value = 0 if term[0] == "=" else 1
        opposite_arg_value = 1 if term[0] == "=" else 0

        self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc + 3)
        self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, arg_value)
        self.add_command(Opcode.JMP, AddressingType.DIRECT, self.pc + 2)
        self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, opposite_arg_value)

    def translate_arithmetic_symbol(self, term, fun_name):
        opcode = arithmetic_symbol_to_opcode(term[0])
        arg1 = term[1]
        arg2 = term[2]

        if re.match(r"\d+", str(arg1)):
            self.operation_with_num_literal(term, Opcode.LOAD, int(arg1))
        else:
            self.operation_with_var(term, Opcode.LOAD, arg1, fun_name)

        if re.match(r"\d+", str(arg2)):
            self.operation_with_num_literal(term, opcode, int(arg2))
        else:
            self.operation_with_var(term, opcode, arg2, fun_name)

    def translate_ampersand(self, term, fun_name):
        cond1 = term[1]
        cond2 = term[2]

        if isinstance(cond1, list):
            self.translate_term(cond1, fun_name)
        else:
            self.operation_with_var(term, Opcode.LOAD, cond1, fun_name)

        self.add_command(Opcode.PUSH)

        if isinstance(cond2, list):
            self.translate_term(cond2, fun_name)
        else:
            self.operation_with_var(term, Opcode.LOAD, cond2, fun_name)

        self.add_command(Opcode.CMP, AddressingType.SP_INDIRECT, 0)
        self.add_command(Opcode.JZ, AddressingType.DIRECT, self.pc + 3)
        self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, 0)
        self.add_command(Opcode.JMP, AddressingType.DIRECT, self.pc + 2)
        self.add_command(Opcode.LOAD, AddressingType.OPERAND_LOAD, 1)
        self.add_command(Opcode.POP)

    def translate_term(self, term, fun_name: str | None = None):
        if term[0] == "fun":
            if fun_name is None:
                self.translate_fun(term)
                return
            raise TermError(term, "You can't define function inside other function")

        if term[0] in self.functions.keys():
            self.translate_fun_call(term, fun_name)
            return

        if term[0] == "if":
            self.translate_if(term, fun_name)
            return

        if term[0] == "while":
            self.translate_while(term, fun_name)
            return

        if term[0] == "set":
            self.translate_set(term, fun_name)
            return

        if term[0] == "set_char":
            self.translate_set_char(term, fun_name)
            return

        if term[0] == "print_string":
            self.translate_print_string(term)
            return

        if term[0] == "print_char":
            self.translate_print_char(term, fun_name)
            return

        if term[0] == "print_int":
            self.translate_print_int(term, fun_name)
            return

        if term[0] == "read_char":
            self.translate_read_char()
            return

        if term[0] == "alloc":
            self.translate_alloc(term)
            return

        if term[0] in comparison_symbols():
            self.translate_comparison_symbol(term, fun_name)
            return

        if term[0] == "&":
            self.translate_ampersand(term, fun_name)
            return

        if term[0] in arithmetic_symbols():
            self.translate_arithmetic_symbol(term, fun_name)
            return

        raise TermError(term, "Invalid keyword")

    def translate(self, terms):
        for term in terms:
            self.translate_term(term)

        self.data_memory[0] = command_to_hex(Opcode.JMP, AddressingType.DIRECT, len(self.data_memory))

        for i in range(len(self.code_memory)):
            command = command_from_hex(self.code_memory[i])
            if command[0] == Opcode.JMP or command[0] == Opcode.JZ or command[0] == Opcode.CALL:
                self.code_memory[i] = command_to_hex(command[0], command[1], command[2] + len(self.data_memory))

        self.add_command(Opcode.HLT)
        return self.data_memory + self.code_memory
