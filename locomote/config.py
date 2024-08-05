from dataclasses import dataclass, fields, field
from pathlib import Path
from dacite import from_dict
from tomllib import load
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
    rev: str | None = None
    repo: str | None = None


@dataclass
class FileConfig:
    src: str
    dst: str
    lang: str | None = None
    filename: str | None = None
    src_lang: str | None = None

    @property
    def file(self) -> str:
        return self.src


@dataclass
class Config:
    output: OutputConfig
    diff: DiffConfig | None
    file: FileConfig | None

    @property
    def input(self) -> DiffConfig | FileConfig:
        return self.diff if self.diff else self.file

    @classmethod
    def from_toml(cls, cfg: Path) -> dict[str, "Config"]:
        with open(cfg, "rb") as f:
            data = load(f)
        return {k: from_dict(data_class=cls, data=v) for k, v in data.items()}
