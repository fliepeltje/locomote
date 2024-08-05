from dataclasses import dataclass
from difflib import ndiff

from tiktoken import encoding_for_model

from typing import Literal



@dataclass
class Segment:
    op: Literal["+", "-", " "]
    content: str
    start: int
    
    def token_mods(self) -> list["Segment"]:
        segments = []
        enc = encoding_for_model("gpt-4o")
        tokens = enc.encode(self.content)
        decoded = [enc.decode_single_token_bytes(x).decode() for x in tokens]
        cursor = self.start
        for token in decoded:
            if self.op == "+" or self.op == "-":
                segments.append(Segment(self.op, token, cursor))
            cursor += len(token)
        if self.op == "-":
            return sorted(segments, key=lambda x: x.start, reverse=True)
        return segments

    def __call__(self, sequence: str) -> str:
        if self.op == "+":
            return sequence[: self.start] + self.content + sequence[self.start :]
        elif self.op == "-":
            return sequence[: self.start] + sequence[self.start + len(self.content) :]
        else:
            return sequence

    @classmethod
    def from_diff_line(cls, line: str, cursor_index: int) -> "Segment":
        return cls(line[0], line[2:], cursor_index)

    @classmethod
    def from_diffs(cls, diffs: list[str], cursor: int) -> list["Segment"]:
        segments = []
        for diff in diffs:
            if diff.startswith("?"):
                continue
            segment = cls.from_diff_line(diff, cursor)
            if segment.op == " " or segment.op == "+":
                cursor += len(segment.content)
            segments.append(segment)
        return segments

    @classmethod
    def from_sequences(
        cls,
        seq_old: str,
        seq_new: str,
        scope: Literal["doc", "line", "word"] = "doc",
        cursor: int = 0,
    ) -> list["Segment"]:
        match scope:
            case "doc":
                diffs = ndiff(
                    seq_old.splitlines(keepends=True), seq_new.splitlines(keepends=True)
                )
                segments = cls.from_diffs(diffs, cursor)
                segments = cls.resolve_segments(segments, "line")
                return segments
            case "line":
                old_split = [x + " " for x in seq_old.split(" ")]
                old_split[-1] = old_split[-1][:-1]
                new_split = [x + " " for x in seq_new.split(" ")]
                new_split[-1] = new_split[-1][:-1]
                diffs = ndiff(old_split, new_split)
                segments = cls.from_diffs(diffs, cursor)
                segments = cls.resolve_segments(segments, "word")
                return segments
            case "word":
                diffs = ndiff(seq_old, seq_new)
                segments = cls.from_diffs(diffs, cursor)
                return segments

    @staticmethod
    def resolve_segments(
        segments: list["Segment"], scope: Literal["line", "word"]
    ) -> list["Segment"]:
        resolved = []
        for segment in segments:
            if segment.op == " ":
                resolved.append(segment)
            elif segment.op == "-":
                if resolved and resolved[-1].op == "-":
                    old = resolved.pop()
                    resolved.append(
                        Segment("-", old.content + segment.content, old.start)
                    )
                else:
                    resolved.append(segment)
            else:
                if (
                    resolved
                    and resolved[-1].op == "-"
                    and resolved[-1].start == segment.start
                ):
                    old = resolved.pop()
                    seq_old, seq_new = old.content, segment.content
                    resolved += Segment.from_sequences(
                        seq_old, seq_new, scope, old.start
                    )
                elif resolved and resolved[-1].op == "+":
                    old = resolved.pop()
                    resolved.append(
                        Segment("+", old.content + segment.content, old.start)
                    )
                else:
                    resolved.append(segment)
        return resolved
