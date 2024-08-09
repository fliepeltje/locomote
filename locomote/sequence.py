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
class Diff:
    add_content: str | None
    rm_content: str | None
    cursor: int

    @classmethod
    def from_ndiff(cls, ndiffs: list[str], cursor: int = 0) -> list["Diff"]:
        diffs = []
        for line in ndiffs:
            op = line[0]
            content = line[2:]
            if op == "+":
                if diffs and diffs[-1].rm_content and diffs[-1].cursor == cursor:
                    prev = diffs.pop()
                    diffs.append(cls(content, prev.rm_content, cursor))
                else:
                    diffs.append(cls(content, None, cursor))
                cursor += len(content)
            elif op == "-":
                diffs.append(cls(None, content, cursor))
            elif op == " ":
                cursor += len(content)
        return diffs

    def __call__(self, sequence: str) -> str:
        if self.add_content:
            seq = sequence[: self.cursor] + self.add_content + sequence[self.cursor :]
        elif self.rm_content:
            seq = (
                sequence[: self.cursor] + sequence[self.cursor + len(self.rm_content) :]
            )
        self.result = seq
        return seq

    @staticmethod
    def resolve(diffs: list["Diff"]) -> list["Diff"]:
        resolved = []
        deletes = []
        for diff in diffs:
            if diff.rm_content and not diff.add_content:
                deletes.append(diff)
                continue
            if diff.rm_content and diff.add_content:
                deletes.append(Diff(None, diff.rm_content, diff.cursor))
            if diff.add_content and deletes:
                del_offset = 0
                del_diffs = []
                for delete in deletes:
                    del_diff = Diff(None, delete.rm_content, delete.cursor + del_offset)
                    del_offset += len(delete.rm_content)
                    del_diffs.append(del_diff)
                resolved += reversed(del_diffs)
                deletes = []
            resolved.append(diff)
        return resolved


@dataclass
class Sequence:
    start: str
    end: str
    speed: Speed = "token"
    max_line_display: int | None = None
    max_line_chars: int | None = None

    @property
    def line_diffs(self) -> list[Diff]:
        return Diff.from_ndiff(
            ndiff(
                self.start.splitlines(keepends=True), self.end.splitlines(keepends=True)
            )
        )

    @property
    def token_diffs(self) -> list[Diff]:
        diffs = []
        for diff in self.line_diffs:
            start_tokens = get_tokens(diff.rm_content or "")
            end_tokens = get_tokens(diff.add_content or "")
            token_diffs = Diff.from_ndiff(ndiff(start_tokens, end_tokens), diff.cursor)
            diffs += token_diffs
        return Diff.resolve(diffs)

    def width(self, char_width: int) -> int:
        if self.max_line_chars:
            return self.max_line_chars * char_width
        all_lines = self.start.splitlines() + self.end.splitlines()
        longest_line_length = max([len(line) for line in all_lines])
        return longest_line_length * char_width

    def height(self, char_height: int) -> int:
        if self.max_line_display:
            return self.max_line_display * char_height
        start_height = len(self.start.splitlines()) * char_height
        end_height = len(self.end.splitlines()) * char_height
        return max(start_height, end_height)

    def display(self, seq: str) -> str:
        if self.max_line_display:
            seq = "\n".join(seq.splitlines()[-self.max_line_display :])
        if self.max_line_chars:
            seq = "\n".join(line[: self.max_line_chars] for line in seq.splitlines())
        return seq

    def __iter__(self):
        seq = self.start
        yield self.display(seq)
        if self.speed == "line":
            diffs = self.line_diffs
        elif self.speed == "token":
            diffs = self.token_diffs
        for diff in diffs:
            seq = diff(seq)
            yield self.display(seq)
        yield self.display(self.end)
