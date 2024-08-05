from dataclasses import dataclass, field
from pathlib import Path
from dacite import from_dict
from toml import load
from typing import Literal


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
    rev: str | None = None # specified as commitFrom..commitTo
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
