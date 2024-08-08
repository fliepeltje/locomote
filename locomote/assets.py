from numpy import array as np_array
from moviepy.editor import ImageSequenceClip

from PIL import ImageDraw, Image
from PIL.Image import Image as ImageT

from locomote.config import Cfg
from locomote.draw.window import Window, WindowCtl
from locomote.draw.code import LoC


async def initialize_base_still(cfg: Cfg, code_w: int, code_h: int) -> ImageT:
    window = await Window.from_cfg(cfg, code_w, code_h)
    window_ctl = await WindowCtl.from_cfg(cfg, window.width)
    size = (
        window.width + (2 * cfg.output.margin),
        window.height + (2 * cfg.output.margin),
    )
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    await window(draw)
    if cfg.output.window_ctl:
        await window_ctl(draw)
    return image


async def create_still(base: ImageT, loc: list[LoC]) -> ImageT:
    img = base.copy()
    draw = ImageDraw.Draw(img)
    for l in loc:
        await l(draw)
    return img


async def create_clip(stills: list[ImageT], fps: int) -> ImageSequenceClip:
    arrays = [np_array(img) for img in stills]
    return ImageSequenceClip(arrays, fps=fps)
