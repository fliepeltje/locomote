from locomote.parser import *


def test_sgement_from_diff_line():
    line = "- from fastapi import FastAPI, Request\n"
    segment = Segment.from_diff_line(line, 0)
    assert segment.op == "-"
    assert segment.content == "from fastapi import FastAPI, Request\n"
    assert segment.start == 0


def test_segment_from_diffs():
    diffs = [
        "- from fastapi import FastAPI, Request\n",
        "+ import os\n",
        "  from fastapi import FastAPI\n"
    ]
    segments = Segment.from_diffs(diffs, 0)
    assert len(segments) == 3
    assert segments[0].op == "-"
    assert segments[0].content == "from fastapi import FastAPI, Request\n"
    assert segments[0].start == 0
    assert segments[1].op == "+"
    assert segments[1].content == "import os\n"
    assert segments[1].start == 0
    assert segments[2].op == " "
    assert segments[2].content == "from fastapi import FastAPI\n"
    assert segments[2].start == len("import os\n")


def test_segment_call():
    segment = Segment("+", "import os\n", 0)
    seq_old = """
from fastapi import FastAPI, Response
""".strip()
    res = segment(seq_old)
    assert res == """
import os
from fastapi import FastAPI, Response
""".strip()

    segment = Segment("-", "from fastapi", 0)
    seq_old = """from fastapi import FastAPI, Response"""
    assert segment(seq_old) == """ import FastAPI, Response"""

def test_segment_from_sequences():
    seq_old = """
from fastapi import FastAPI, Response

app = FastAPI()
""".strip()
    seq_new = """
import os

app = FastAPI()
foo = "bar"
""".strip()
    segments = Segment.from_sequences(seq_old, seq_new)
    char_mods = []
    for seg in segments:
        char_mods += seg.char_mods()
    res = seq_old
    for seg in char_mods:
        res = seg(res)
    assert res == seq_new
    