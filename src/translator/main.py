import pickle
import sys

from src.isa import hex_to_mnemonic
from src.translator.lexer import Lexer
from src.translator.translator import Translator


def translate(text):
    lexer = Lexer()
    translator = Translator()

    memory = translator.translate(lexer.text_to_terms(text))

    debug = [f"{0} - {memory[0]} - {hex_to_mnemonic(memory[0])}", "\nDATA MEMORY"]

    for i in range(1, len(translator.data_memory)):
        if int(memory[i], 16) > 32:
            debug.append(f"{i} - {memory[i]} - {int(memory[i], 16)} - {chr(int(memory[i], 16))}")
        else:
            debug.append(f"{i} - {memory[i]} - {int(memory[i], 16)}")

    debug.append("\nCODE MEMORY")

    for i in range(len(translator.data_memory), len(memory)):
        debug.append(f"{i} - {memory[i]} - {hex_to_mnemonic(memory[i])}")

    return memory, debug


def main(src_file, debug_dst_file, bin_dst_file):
    with open(src_file, encoding="utf-8") as f:
        source_code = f.read()

    memory, debugging_output = translate(source_code)

    with open(debug_dst_file, "w", encoding="utf-8") as f:
        f.write("\n".join(debugging_output))

    with open(bin_dst_file, "wb") as f:
        pickle.dump(memory, f)

    print("source LoC:", len(source_code.split("\n")), "machine code instr:", len(memory))


if __name__ == "__main__":
    assert len(sys.argv) == 2, "Wrong arguments: main.py <input_file>"
    _, src = sys.argv

    debug_dst, bin_dst = "../translator-output/debug", "../translator-output/binary"
    main(src, debug_dst, bin_dst)
