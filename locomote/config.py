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
    exports: list[Literal["clip", "stills", "gif"]]

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



@dataclass
class CmdCfg:
    command: str
    logfile: str
    host_ctx: str | None = None

    # @property
    # def raw(self) -> tuple[RawCfg, RawCfg]:
    #     ctx_line = f"{self.host_ctx} " if self.host_ctx else ""
    #     cmd = RawCfg(ctx_line, ctx_line + self.command)
    #     with open(self.logfile, "r") as f:
    #         out_content = f.read()
    #     out_start = ctx_line + self.command + "\n"
    #     out = RawCfg(seq_start=out_start, seq_end=out_start + "\n" + out_content)
    #     return cmd, out

    # @property
    # def max_lines(self) -> int:
    #     return self.raw[1].max_lines

    # @property
    # def max_line_chars(self) -> int:
    #     return self.raw[1].max_line_chars

    # @property
    # def seq_widest(self) -> str:
    #     return self.raw[1].seq_widest

    # @property
    # def seq_longest(self) -> str:
    #     return self.raw[1].seq_longest


@dataclass
class Cfg:
    input: RawCfg | FileCfg | DiffCfg | CmdCfg
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
    def spaced_char_height(self) -> int:
        return self.char_box[1] + self.output.line_spacing
    
