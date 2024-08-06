from dataclasses import dataclass, field
from pathlib import Path
from dacite import from_dict
from git import Repo, Commit
from toml import load
from typing import Literal


@dataclass
class OutputCfg:
    path: str
    exports: list[Literal["clip", "stills"]]

    # Box limits
    min_width: int | None = None
    width: int | None = None
    max_width: int | None = None
    min_height: int | None = None
    height: int | None = None
    max_height: int | None = None

    # Code Styling
    font_name: str = "Hack Nerd Font"
    font_size: int = 14
    style: str = "lightbulb"
    indent_size: int = 2
    line_spacing: int = 5
    max_line_display: int | None = None
    padding_horizontal: int = 40
    padding_vertical: int = 40

    # Window Styling
    window_ctl: bool = True
    window_title: str | None = None


@dataclass
class RawCfg:
    seq_start: str
    seq_end: str

    @property
    def _start_widest_line(self) -> str:
        return max(self.seq_start.splitlines(), key=len) if self.seq_start else ""

    @property
    def _end_widest_line(self) -> str:
        return max(self.seq_end.splitlines(), key=len) if self.seq_end else ""

    @property
    def _start_line_count(self) -> int:
        return len(self.seq_start.splitlines())

    @property
    def _end_line_count(self) -> int:
        return len(self.seq_end.splitlines())

    @property
    def max_lines(self) -> int:
        return max(self._start_line_count, self._end_line_count)

    @property
    def max_line_chars(self) -> int:
        return max(len(self._start_widest_line), len(self._end_widest_line))

    @property
    def seq_widest(self) -> str:
        if self._start_widest_line > self._end_widest_line:
            return self._start_widest_line
        return self._end_widest_line

    @property
    def seq_longest(self) -> str:
        if self._start_line_count > self._end_line_count:
            return self.seq_start
        return self.seq_end


@dataclass
class FileCfg:
    seq_end_file: str
    seq_start_file: str | None = None

    @property
    def raw(self) -> RawCfg:
        with open(self.seq_end_file, "r") as f:
            seq_end = f.read()
        if self.seq_start_file:
            with open(self.seq_start_file, "r") as f:
                seq_start = f.read()
        else:
            seq_start = ""
        return RawCfg(seq_start, seq_end)

    @property
    def max_lines(self) -> int:
        return self.raw.max_lines

    @property
    def max_line_chars(self) -> int:
        return self.raw.max_line_chars

    @property
    def seq_widest(self) -> str:
        return self.raw.seq_widest

    @property
    def seq_longest(self) -> str:
        return self.raw.seq_longest


@dataclass
class DiffCfg:
    file: str
    rev: str | None = None
    repo: str | None = None

    @property
    def commits(self) -> list[Commit]:
        repo = Repo(self.repo) if self.repo else Repo(".")
        return sorted(
            [x for x in repo.iter_commits(rev=self.rev, paths=self.file)],
            key=lambda x: x.committed_datetime,
        )

    def content_for(self, commit: Commit) -> str:
        return commit.tree[str(self.file)].data_stream.read().decode()

    @property
    def raw(self) -> list[tuple[Commit, RawCfg]]:
        raws = []
        for idx in range(1, len(self.commits)):
            raw_cfg = RawCfg(
                self.content_for(self.commits[idx - 1]),
                self.content_for(self.commits[idx]),
            )
            raws.append((self.commits[idx], raw_cfg))
        return raws

    @property
    def max_lines(self) -> int:
        return max(raw_cfg.max_lines for _, raw_cfg in self.raw)

    @property
    def max_line_chars(self) -> int:
        return max(raw_cfg.max_line_chars for _, raw_cfg in self.raw)

    @property
    def seq_widest(self) -> str:
        seqs = [(x.seq_widest, x.max_line_chars) for _, x in self.raw]
        return max(seqs, key=lambda x: x[1])[0]

    @property
    def seq_longest(self) -> str:
        seqs = [(x.seq_longest, x.max_lines) for _, x in self.raw]
        return max(seqs, key=lambda x: x[1])[0]


@dataclass
class CmdCfg:
    command: str
    logfile: str
    host_ctx: str | None = None

    @property
    def raw(self) -> tuple[RawCfg, RawCfg]:
        ctx_line = f"{self.host_ctx} " if self.host_ctx else ""
        cmd = RawCfg(ctx_line, ctx_line + self.command)
        with open(self.logfile, "r") as f:
            out_content = f.read()
        out = RawCfg(seq_start=ctx_line, seq_end=ctx_line + "\n" + out_content)
        return cmd, out

    @property
    def max_lines(self) -> int:
        return self.raw[1].max_lines

    @property
    def max_line_chars(self) -> int:
        return self.raw[1].max_line_chars

    @property
    def seq_widest(self) -> str:
        return self.raw[1].seq_widest

    @property
    def seq_longest(self) -> str:
        return self.raw[1].seq_longest


@dataclass
class InputCfg:
    cfg: RawCfg | FileCfg | DiffCfg | CmdCfg
    lang: str


@dataclass
class Cfg:
    input: InputCfg
    output: OutputCfg


@dataclass
class PILConfig:
    width: int = 600
    height: int = 400
    font_name: str = "Hack Nerd Font"
    font_size: int = 14
    image_pad: int = 40
    style: str = "lightbulb"


@dataclass
class AssetConfig:
    clip: bool = True
    head_img: bool = True
    tail_img: bool = True


@dataclass
class OutputConfig:
    path: str
    type: Literal["code-block", "terminal-output"] = "code-block"
    pil: PILConfig = field(default_factory=PILConfig)
    assets: AssetConfig = field(default_factory=AssetConfig)


@dataclass
class DiffConfig:
    file: str
    lang: str | None = None
    rev: str | None = None  # specified as commitFrom..commitTo
    repo: str | None = None


@dataclass
class FileConfig:
    dst: str
    src: str | None = None
    lang: str | None = None
    filename: str | None = None
    src_lang: str | None = None

    @property
    def file(self) -> str:
        return self.dst

    @property
    def seq_a(self) -> str:
        if not self.src:
            return ""
        with open(self.src, "r") as f:
            text = f.read()
        return text

    @property
    def seq_b(self) -> str:
        with open(self.dst, "r") as f:
            text = f.read()
        return text

    @property
    def max_lines(self) -> str:
        return max(len(self.seq_a.splitlines()), len(self.seq_b.splitlines()))


@dataclass
class CmdConfig:
    cmd: str
    logfile: str
    lang: str = "bash"
    host_line: str | None = None
    logline_display: int = 15

    @property
    def file(self):
        return None


@dataclass
class Config:
    output: OutputConfig
    diff: DiffConfig | None = None
    file: FileConfig | None = None
    cmd: CmdConfig | None = None

    @property
    def input(self) -> DiffConfig | FileConfig:
        configs = [x for x in [self.diff, self.file, self.cmd] if x]
        if len(configs) != 1:
            raise ValueError("Exactly config must be provided")
        return configs[0]

    @classmethod
    def from_toml(cls, cfg: Path) -> dict[str, "Config"]:
        with open(cfg, "r") as f:
            data = load(f)
        return {k: from_dict(data_class=cls, data=v) for k, v in data.items()}
