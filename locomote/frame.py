import logging
from dataclasses import dataclass
from PIL import Image
from PIL.Image import Image as ImageT
from PIL.ImageFont import ImageFont
from PIL.ImageDraw import ImageDraw
from pygments.lexer import Lexer
from pygments.style import Style
from pygments.formatters.img import FontManager

logger = logging.getLogger("pil")


async def window_img(width: int, height: int, bg_color: str = "#FFFFFF") -> ImageT:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw(img)
    draw.rounded_rectangle(
        (0, 0, width, height),
        fill=bg_color,
        radius=15,
    )
    return img


async def window_ctl_img(width: int, font: ImageFont, title: str = " ") -> ImageT:
    titlebox = font.getbbox("M")
    height = titlebox[1] + titlebox[3]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw(image)
    circle_margin_h = 4
    circle_margin_w = 10
    radius = (height // 2) - (circle_margin_h * 2)
    circle_w = radius * 2
    pos_y = circle_margin_h * 2 + radius
    for idx, color in enumerate(["#FF605C", "#FFBD44", "#00CA4E"]):
        pos_x = radius + circle_w * idx + circle_margin_w * (idx + 1)
        draw.circle(
            (pos_x, pos_y),
            radius,
            fill=color,
        )
    title_start = (width - font.getbbox(title)[2]) // 2
    title_x = title_start
    draw.text(
        (title_x, titlebox[1]),
        title,
        font=font,
        fill=(128, 128, 128),
    )
    draw.line(
        [
            (0, height),
            (width, height),
        ],
        fill=(128, 128, 128),
    )
    return image


@dataclass
class CodeDisplay:
    lexer: Lexer
    style: Style
    font_manager: FontManager
    token_styles: dict
    line_height: int

    async def __call__(
        self,
        draw: ImageDraw,
        code: str,
    ) -> None:
        lineno = 0
        drawn = ""
        for token, token_content in self.lexer.get_tokens(code):
            if token_content == "\n":
                lineno += 1
                drawn = ""
                continue
            while token not in self.token_styles:
                token = token.parent
            style = self.token_styles[token]
            color = f"#{style.get('color', 'fff')}"
            font = self.font_manager.get_font(style["bold"], style["italic"])
            draw.text(
                (font.getbbox(drawn)[2], lineno * self.line_height),
                token_content,
                font=font,
                fill=color,
            )
            drawn += token_content
            if token_content.endswith("\n"):
                lineno += 1
                drawn = ""


async def code_img(
    blocks: list[tuple[CodeDisplay, str]],
    width: int,
    height: int,
) -> ImageT:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    offset_y = 0
    for display, code in blocks:
        code_h = len(code.splitlines()) * display.line_height
        code_img = Image.new(
            "RGBA",
            (width, code_h),
            (0, 0, 0, 0),
        )
        draw = ImageDraw(code_img)
        await display(draw, code)
        image.paste(code_img, (0, offset_y))

        offset_y += code_img.height
    return image


async def still(
    window: ImageT,
    code: ImageT,
    margin: int = 30,
    window_ctl: ImageT | None = None,
    bg_color: str = "#00B140",
    code_padding_x: int = 80,
    code_padding_y: int = 10,
) -> ImageT:
    base = Image.new(
        "RGBA",
        (
            window.width + (margin * 2),
            window.height + (margin * 2),
        ),
        bg_color,
    )
    base.paste(window, (margin, margin), window)
    code_offset_y = margin + code_padding_y
    if window_ctl:
        base.paste(window_ctl, (margin, margin), window_ctl)
        code_offset_y += window_ctl.height

    base.paste(code, (margin + code_padding_x, code_offset_y), code)
    return base
