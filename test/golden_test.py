import contextlib
import io
import logging
import os
import tempfile

import pytest
from src.machine import machine
from src.translator import main


@pytest.mark.golden_test("../golden/*.yml")
def test_whole_by_golden(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdirname:
        source = os.path.join(tmpdirname, "source")
        input_stream = os.path.join(tmpdirname, "input")
        target = os.path.join(tmpdirname, "target")
        target_bin = os.path.join(tmpdirname, "target_bin")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["input"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            main.main(source, target, target_bin)
            print("============================================================")
            machine.main(target_bin, input_stream)

        with open(target, encoding="utf-8") as file:
            code = file.read()

        assert code == golden.out["code"]
        assert stdout.getvalue() == golden.out["output"]
        assert caplog.text == golden.out["log"]
