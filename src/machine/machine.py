import logging
import pickle
import sys

from src.machine.control_unit import ControlUnit
from src.machine.data_path import DataPath


def simulation(memory, input_tokens, limit):
    data_path = DataPath(memory, input_tokens)
    control_unit = ControlUnit(data_path)
    instr_counter = 0

    logging.debug("%s", control_unit)
    try:
        while instr_counter < limit:
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.debug("%s", control_unit)

    except EOFError:
        logging.warning("Input buffer is empty!")

    except StopIteration:
        pass

    if instr_counter >= limit:
        logging.warning("Limit exceeded!")

    return "".join(data_path.output_buffer), instr_counter, control_unit._tick


def main(bin_code_file, input_file):
    with open(bin_code_file, "rb") as f:
        memory = pickle.load(f)

    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)
        input_token.append("\0")

    output, instr_counter, ticks = simulation(memory, input_token, limit=1000)

    print(output)
    print(f"instr_counter: {instr_counter}, ticks: {ticks}")


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <binary_code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
