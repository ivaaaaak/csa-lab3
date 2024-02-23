from __future__ import annotations

import re

from src.translator.errors import InvalidSymbolsError


def boolean_literal():
    return {"T", "F"}


def arithmetic_symbols():
    return {"+", "-", "%"}


def comparison_symbols():
    return {"=", "!="}


class Lexer:
    def __init__(self):
        self.all_terms = []
        self.terms_stack = []
        self.brackets_num = 0

        self.cur_term = []
        self.atom = []

    def process_string_char(self, char):
        self.atom.append(char)

        if char == "'":
            self.cur_term.append("".join(self.atom))
            self.atom = []

    def process_left_parenthesis(self):
        if self.brackets_num != 0:
            self.terms_stack.append(self.cur_term)
            self.cur_term = []
        self.brackets_num += 1

    def process_right_parenthesis(self):
        if len(self.atom) != 0:
            self.cur_term.append("".join(self.atom))
            self.atom = []

        if self.brackets_num > 1:
            prev_list = self.terms_stack.pop()
            prev_list.append(self.cur_term)
            self.cur_term = prev_list

        if self.brackets_num == 1:
            self.all_terms.append(self.cur_term)
            self.cur_term = []

        self.brackets_num -= 1

    def process_char(self, line_num, pos, char):
        if re.match(r"'.*\n*", "".join(self.atom)):
            self.process_string_char(char)

        elif char == "(":
            self.process_left_parenthesis()

        elif char == ")":
            self.process_right_parenthesis()

        elif re.match(r"\s", char):
            if len(self.atom) != 0:
                self.cur_term.append("".join(self.atom))
                self.atom = []

        elif (
            re.match(r"\w", char)
            or (char == "'" and len(self.atom) == 0)
            or char in arithmetic_symbols()
            or char in comparison_symbols()
            or char == "!"
            or char == "&"
        ):
            self.atom.append(char)

        else:
            raise InvalidSymbolsError(line_num, pos, char)

    def text_to_terms(self, text) -> list[str]:
        for line_num, line in enumerate(text.split("\n"), 1):
            for pos, char in enumerate(line, 1):
                self.process_char(line_num, pos, char)

        return self.all_terms
