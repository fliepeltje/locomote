from dataclasses import dataclass
from functools import cached_property

from pygments.formatters.img import FontManager
from pygments.lexer import Lexer
from pygments.style import Style
from PIL.ImageDraw import ImageDraw

from locomote.config import Cfg


@dataclass
class LoC:
    content: str
    cfg: Cfg
    lexer: Lexer
    offset_y: int = 0

    @property
    def offset_x(self) -> int:
        return self.cfg.output.margin + self.cfg.output.padding_horizontal

    @property
    def base_offset_y(self) -> int:
        return (
            self.offset_y
            + self.cfg.output.margin
            + self.cfg.spaced_char_height
        )

    @property
    def font_manager(self) -> FontManager:
        return self.cfg.font_manager

    @property
    def style(self) -> Style:
        return self.cfg.style

    @cached_property
    def token_styles(self) -> dict[str, str]:
        return dict(self.style)

    async def __call__(self, draw: ImageDraw):
        offset_y, offset_x = self.base_offset_y, self.offset_x
        if self.cfg.output.window_ctl:
            offset_y += self.cfg.spaced_char_height
        tokens = self.lexer.get_tokens(self.content)
        for token, content in tokens:
            if content == "\n":
                offset_y += self.cfg.spaced_char_height
                offset_x = self.offset_x
                continue
            while token not in self.token_styles:
                token = token.parent
            style = self.token_styles[token]
            font = self.font_manager.get_font(style["bold"], style["italic"])
            draw.text(
                (offset_x, offset_y),
                content,
                font=font,
                fill=f"#{style.get("color", "fff")}",
            )
            if content.endswith("\n"):
                offset_y += self.cfg.spaced_char_height
                offset_x = self.offset_x
                continue
            offset_x += font.getbbox(content)[2]
