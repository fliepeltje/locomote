from dataclasses import dataclass
from locomote.config import Cfg
from PIL.ImageFont import ImageFont
from PIL.ImageDraw import ImageDraw


@dataclass
class Window:
    width: int
    height: int
    offset_x: int
    offset_y: int
    color: int

    @classmethod
    async def from_cfg(cls, cfg: Cfg, code_w: int, code_h: int) -> "Window":
        offset_x, offset_y = cfg.output.margin, cfg.output.margin
        padding_w, padding_h = (
            cfg.output.padding_horizontal,
            cfg.output.padding_vertical,
        )
        ctl_h = (
            cfg.spaced_char_height if cfg.output.window_ctl else 0
        )
        width = code_w + (2 * padding_w)
        if cfg.output.min_width and cfg.output.min_width > width:
            width = cfg.output.min_width
        elif cfg.max_line_chars:
            width = (cfg.max_line_chars * cfg.char_box[0]) + (2 * padding_w)
        else:
            width = code_w + (2 * padding_w)
        height = code_h + padding_h * 2 + ctl_h
        if cfg.output.min_height and cfg.output.min_height > height:
            height = cfg.output.min_height
        height = cfg.output.height or height
        return cls(width, height, offset_x, offset_y, cfg.bg_color)

    async def __call__(self, draw: ImageDraw):
        draw.rounded_rectangle(
            (
                self.offset_x,
                self.offset_y,
                self.offset_y + self.width,
                self.height,
            ),
            fill=self.color,
            radius=10,
        )


@dataclass
class WindowCtl:
    width: int
    height: int
    offset_x: int
    offset_y: int
    title: str
    font: ImageFont

    @classmethod
    async def from_cfg(cls, cfg: Cfg, window_w: int) -> "WindowCtl":
        offset_x, offset_y = cfg.output.margin, cfg.output.margin
        height = (
            cfg.spaced_char_height if cfg.output.window_ctl else 0
        )
        width = window_w
        return cls(
            width,
            height,
            offset_x,
            offset_y,
            cfg.output.window_title or "",
            cfg.default_font,
        )

    async def __call__(self, draw: ImageDraw):
        circle_margin_h = 4
        circle_margin_w = 10
        radius = (self.height // 2) - (circle_margin_h * 2)
        circle_w = radius * 2
        pos_y = self.offset_y + circle_margin_h * 2 + radius
        for idx, color in enumerate(["#FF605C", "#FFBD44", "#00CA4E"]):
            pos_x = (
                self.offset_x + radius + circle_w * idx + circle_margin_w * (idx + 1)
            )
            draw.circle(
                (pos_x, pos_y),
                radius,
                fill=color,
            )
        draw.line(
            [
                (self.offset_x, self.offset_y + self.height),
                (self.offset_x + self.width, self.offset_y + self.height),
            ],
            fill=(128, 128, 128),
        )
        title_offset = 2
        title_start = (self.width - self.font.getbbox(self.title)[2]) // 2
        title_x = self.offset_x + title_start
        title_y = self.offset_y + title_offset
        draw.text(
            (title_x, title_y),
            self.title,
            font=self.font,
            fill=(128, 128, 128),
        )
