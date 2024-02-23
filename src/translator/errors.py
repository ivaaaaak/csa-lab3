class InvalidSymbolsError(Exception):
    def __init__(self, line_num, pos, char):
        self.line_num = line_num
        self.char = char
        self.pos = pos

    def __str__(self):
        return f"Invalid symbol: {self.char}, on line and position: {self.line_num}, {self.pos}"


class TermError(Exception):
    def __init__(self, term, error_string):
        self.term = term
        self.error_string = error_string

    def __str__(self):
        return self.error_string + f" - {self.term}"
