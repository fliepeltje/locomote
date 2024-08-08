from dataclasses import dataclass
from git import Repo, Commit
from typing import Literal
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from functools import cached_property
from PIL import ImageFont
from pygments.formatters.img import FontManager


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
    font_name: str = "JetBrainsMono Nerd Font"
    font_size: int = 14
    style: str = "monokai"
    max_line_display: int | None = None
    padding_horizontal: int = 70
    padding_vertical: int = 40

    # Window Styling
    window_ctl: bool = True
    window_title: str | None = None

    # Image settings
    margin: int = 30

    # Render settings
    fps: int = 10
    speed: Literal["line", "token"] = "token"


@dataclass
class RawCfg:
    seq_start: str
    seq_end: str
    lang: str


@dataclass
class FileCfg:
    seq_end_file: str
    lang: str
    seq_start_file: str | None = None


@dataclass
class DiffCfg:
    file: str
    lang: str
    rev_start: str
    rev_end: str
    repo_path: str | None = None

    @cached_property
    def repo(self) -> Repo:
        return Repo(self.repo_path) if self.repo_path else Repo(".")

    @cached_property
    def commit_start(self) -> Commit:
        return self.repo.commit(self.rev_start)

    @cached_property
    def commit_end(self) -> Commit:
        return self.repo.commit(self.rev_end)

    @property
    def seq_start(self) -> str:
        return self.content_for(self.commit_start)

    @property
    def seq_end(self) -> str:
        return self.content_for(self.commit_end)

    def content_for(self, commit: Commit) -> str:
        try:
            return commit.tree[str(self.file)].data_stream.read().decode()
        except KeyError:
            return ""


@dataclass
class DiffRangeCfg:
    file: str
    lang: str
    rev_range: str
    repo_path: str | None = None

    @property
    def commits(self) -> list[Commit]:
        repo = Repo(self.repo_path) if self.repo_path else Repo(".")
        return sorted(
            [x for x in repo.iter_commits(rev=self.rev_range, paths=self.file)],
            key=lambda x: x.committed_datetime,
        )

    @property
    def diff_cfgs(self) -> list[DiffCfg]:
        cfgs = []
        for i in range(len(self.commits) - 1):
            cfgs.append(
                DiffCfg(
                    file=self.file,
                    lang=self.lang,
                    rev_start=self.commits[i].hexsha,
                    rev_end=self.commits[i + 1].hexsha,
                    repo_path=self.repo_path,
                )
            )
        return cfgs


@dataclass
class CmdCfg:
    command: str
    logfile: str | None = None
    prompt: str | None = None


@dataclass
class Cfg:
    input: RawCfg | FileCfg | DiffCfg | CmdCfg | DiffRangeCfg
    output: OutputCfg
    name: str | None = None

    @cached_property
    def lexer(self):
        return get_lexer_by_name(self.input.lang)

    @cached_property
    def style(self):
        return get_style_by_name(self.output.style)

    @cached_property
    def token_styles(self):
        return dict(self.style)

    @cached_property
    def font_manager(self) -> FontManager:
        font_name = self.output.font_name
        font_size = self.output.font_size
        return FontManager(font_name=font_name, font_size=font_size)

    @cached_property
    def bg_color(self) -> str:
        return f"{self.style.background_color}"

    @cached_property
    def default_font(self) -> ImageFont:
        return self.font_manager.get_font(False, False)

    @cached_property
    def char_box(self) -> tuple[int, int]:
        return self.default_font.getbbox("M")[2:4]
    
    @cached_property
    def max_line_display(self) -> int | None:
        if self.output.max_line_display:
            return self.output.max_line_display
        height = self.output.height or self.output.max_height
        if not height:
            return None
        code_height = height - (self.output.padding_vertical * 2) - (self.output.margin * 2)
        return code_height // self.spaced_char_height

    @cached_property
    def max_line_chars(self) -> int | None:
        if not self.output.max_width and not self.output.width:
            return None
        max_width = self.output.width or self.output.max_width
        max_code_width = max_width - self.output.padding_horizontal
        max_line_chars = max_code_width // self.char_box[0]
        return max_line_chars

    @cached_property
    def spaced_char_height(self) -> int:
        line_spacing = 10
        return self.char_box[1] + line_spacing
