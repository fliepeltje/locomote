from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from pygments.formatters.img import FontManager
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from locomote.config import RawCfg, OutputCfg, InputCfg
from typing import AsyncIterator, Iterator
from functools import cached_property


Box = tuple[int, int]
Offset = tuple[int, int]


@dataclass
class LexedToken:
    content: str
    relative_offset: Offset
    font: ImageFont
    color: str

    @classmethod
    def from_sequence(
        cls,
        seq: str,
        font_manager: FontManager,
        styles: dict[str, str],
        lang: str,
        indent_size: int,
        char_box: Box,
        line_spacing: int,
    ) -> Iterator["LexedToken"]:
        offset_x, offset_y = (0, 0)
        tokens = get_lexer_by_name(lang).get_tokens(seq)
        for token, content in tokens:
            while token not in styles:
                token = token.parent
            token_style = styles[token]
            content = content.replace("    ", "\t")
            content = content.expandtabs(indent_size)
            match content:
                case "\n":
                    offset_x = 0
                    offset_y += char_box[1] + line_spacing
                    continue
                case _:
                    font = font_manager.get_font(
                        token_style["bold"], token_style["italic"]
                    )
                    color = f"#{token_style.get("color", "000")}"
                    yield cls(content, (offset_x, offset_y), font, color)
                    offset_x += font.getbbox(content)[2]


@dataclass
class Stills:
    input: InputCfg
    output: OutputCfg

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
    def font(self) -> ImageFont:
        return self.font_manager.get_font(False, False)

    @cached_property
    def code_box(self) -> Box:
        seq_width = self.font.getbbox(self.input.cfg.seq_widest)[2]
        line_count = len(self.input.cfg.seq_longest.splitlines())
        seq_height = line_count * self.char_box[1]
        seq_height += (line_count - 1) * self.output.line_spacing
        return (seq_width, seq_height)

    @cached_property
    def char_box(self) -> Box:
        return self.font.getbbox("a")[2:4]

    @cached_property
    def padded_code_box(self) -> Box:
        h_pad = self.output.padding_horizontal
        v_pad = self.output.padding_vertical
        return (self.code_box[0] + 2 * h_pad, self.code_box[1] + 2 * v_pad)

    @cached_property
    def code_start_x(self) -> int:
        return self.window_margin + self.output.padding_horizontal

    @cached_property
    def code_start_y(self) -> int:
        return (
            self.window_margin + self.output.padding_vertical + self.window_ctl_box[1]
        )

    @cached_property
    def window_ctl_box(self) -> Box:
        w = self.padded_code_box[0]
        if self.output.window_ctl and self.output.window_title:
            text_h = self.font.getbbox(self.output.window_title)[3]
            h = text_h + (2 * 2)
            return (w, h)
        elif self.output.window_ctl:
            return (w, 40)
        return (w, 0)

    @cached_property
    def window_box(self) -> Box:
        code_w, code_h = self.padded_code_box
        _, ctl_h = self.window_ctl_box
        return (code_w, code_h + ctl_h)

    @cached_property
    def window_margin(self) -> int:
        return 30

    @cached_property
    def window_offset(self) -> Offset:
        return (self.window_margin, self.window_margin)

    @cached_property
    def image_size(self) -> Box:
        w = self.window_box[0] + (self.window_margin * 2)
        h = self.window_box[1] + (self.window_margin * 2)
        return (w, h)

    @cached_property
    def lexer(self):
        return get_lexer_by_name(self.input.lang)

    async def init_image(self):
        img = Image.new("RGBA", self.image_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        return img, draw

    async def draw_window(self, draw: ImageDraw):
        offset_x, offset_y = self.window_offset
        w, h = self.window_box
        draw.rounded_rectangle(
            (offset_x, offset_y, offset_x + w, offset_y + h),
            fill=self.style.background_color,
            radius=10,
        )

    async def draw_window_ctl(self, draw: ImageDraw):
        if not self.output.window_ctl:
            return
        offset_x, offset_y = self.window_offset
        ctl_w, ctl_h = self.window_ctl_box
        circle_offset_h = 5
        circle_offset_w = 10
        radius = (ctl_h // 2) - (circle_offset_h * 2)
        circle_w = radius * 2
        # Control circles; 2px margin on each side
        draw.circle(
            (
                offset_x + radius + circle_w * 0 + circle_offset_w * 1,
                offset_y + circle_offset_h * 2 + radius,
            ),
            radius,
            fill="#FF605C",
        )
        draw.circle(
            (
                offset_x + radius + circle_w * 1 + circle_offset_w * 2,
                offset_y + circle_offset_h * 2 + radius,
            ),
            radius,
            fill="#FFBD44",
        )
        draw.circle(
            (
                offset_x + radius + circle_w * 2 + circle_offset_w * 3,
                offset_y + circle_offset_h * 2 + radius,
            ),
            radius,
            fill="#00CA4E",
        )
        draw.line(
            [(offset_x, offset_y + ctl_h), (offset_x + ctl_w, offset_y + ctl_h)],
            fill=(128, 128, 128),
        )
        if self.output.window_title:
            title_offset = 2
            title_x = (
                offset_x + (ctl_w - self.font.getbbox(self.output.window_title)[2]) // 2
            )
            title_y = offset_y + title_offset
            draw.text(
                (title_x, title_y),
                self.output.window_title,
                font=self.font,
                fill=(128, 128, 128),
            )

    def draw_token(self, draw: ImageDraw, token: LexedToken):
        offset_x, offset_y = self.code_start_x, self.code_start_y
        offset_x += token.relative_offset[0]
        offset_y += token.relative_offset[1]
        draw.text(
            (offset_x, offset_y), token.content, font=token.font, fill=token.color
        )

    async def create_still(self, base_img: Image, seq: str) -> Image:
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        for token in LexedToken.from_sequence(
            seq,
            self.font_manager,
            self.token_styles,
            self.input.lang,
            self.output.indent_size,
            self.char_box,
            self.output.line_spacing,
        ):
            self.draw_token(draw, token)
        return img
