from dataclasses import dataclass
from difflib import ndiff

from tiktoken import encoding_for_model

from typing import Literal

GptEnc = encoding_for_model("gpt-4o")
Speed = Literal["token", "newline"]

def get_tokens(seq: str) -> list[str]:
    tokens = GptEnc.encode(seq)
    return [GptEnc.decode_single_token_bytes(x).decode() for x in tokens]

@dataclass
class SeqMod:
    op: Literal["+", "-", " "]
    content: str
    start: int

    def __call__(self, sequence: str) -> str:
        if self.op == "+":
            return sequence[: self.start] + self.content + sequence[self.start :]
        elif self.op == "-":
            return sequence[: self.start] + sequence[self.start + len(self.content) :]
        else:
            return sequence

    @classmethod
    def from_diff_line(cls, line: str, cursor_index: int) -> "SeqMod":
        return cls(line[0], line[2:], cursor_index)

    @classmethod
    def from_diffs(cls, diffs: list[str], cursor: int) -> list["SeqMod"]:
        mods = []
        for diff in diffs:
            if diff.startswith("?"):
                continue
            seq_mod = cls.from_diff_line(diff, cursor)
            if seq_mod.op == " " or seq_mod.op == "+":
                cursor += len(seq_mod.content)
            mods.append(seq_mod)
        return mods

    @classmethod
    def from_sequences(
        cls,
        seq_old: str,
        seq_new: str,
        speed: Speed = "token",
        cursor: int = 0,
    ) -> list["SeqMod"]:
        match speed:
            case "newline":
                diffs = ndiff(
                    seq_old.splitlines(keepends=True), 
                    seq_new.splitlines(keepends=True)
                )
                mods = cls.from_diffs(diffs, cursor)
                return mods
            case "token":
                resolved = []
                line_mods = cls.from_sequences(seq_old, seq_new, "newline", cursor)
                for line_seg in line_mods:
                    if line_seg.op == " " or not resolved:
                        resolved.append(line_seg)
                        continue
                    if resolved[-1].op == "-" and line_seg.op == "+":
                        prev = resolved.pop()
                        seq_old, seq_new = prev.content, line_seg.content
                        old_split, new_split = get_tokens(seq_old), get_tokens(seq_new)
                        diffs = ndiff(old_split, new_split)
                        resolved += cls.from_diffs(diffs, prev.start)
                    else:
                        resolved.append(line_seg)
                return resolved


# async def generate_text_iter(
#     sequence_start: str, 
#     sequence_end: str,
#     speed: Speed = "token"
# ) -> AsyncIterator[str]:
#     yield sequence_start
#     if speed == "token":
#         segments = Segment.from_sequences(sequence_start, sequence_end)
#         for seg in segments:
#             for mod in seg.token_mods():
#                 sequence_start = mod(sequence_start)
#                 yield sequence_start
#     elif speed == "newline":
#         segments = Segment.from_sequences(sequence_start, sequence_end, "newline")
#         for seg in segments:
#             sequence_start = seg(sequence_start)
#             yield sequence_start
#     yield sequence_end


