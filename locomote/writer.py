import os

from PIL import Image, ImageDraw, ImageFont

from pygments import highlight 
from pygments.lexers import Python3Lexer 
from pygments.formatters import ImageFormatter 

from moviepy.video.io import ImageSequenceClip

class PilFormatter(ImageFormatter):

    def __init__(
            self, 
            width: int, 
            height: int,
            bg_transparent: bool = False,
            **options
        ):
        super().__init__(**options)
        self.width = width
        self.height = height
        if bg_transparent:
            self.background_color = (0, 0, 0, 0)

    def format(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        This implementation calculates where it should draw each token on the
        pixmap, then calculates the required pixmap size and draws the items.
        """
        self._create_drawables(tokensource)
        self._draw_line_numbers()
        im = Image.new(
            'RGB',
            (self.width, self.height),
            self.background_color,
        )
        self._paint_line_number_bg(im)
        draw = ImageDraw.Draw(im)
        # Highlight
        if self.hl_lines:
            x = self.image_pad + self.line_number_width - self.line_number_pad + 1
            recth = self._get_line_height()
            rectw = im.size[0] - x
            for linenumber in self.hl_lines:
                y = self._get_line_y(linenumber - 1)
                draw.rectangle([(x, y), (x + rectw, y + recth)], fill=self.hl_color)
        for pos, value, font, text_fg, text_bg in self.drawables:
            if text_bg:
                # see deprecations https://pillow.readthedocs.io/en/stable/releasenotes/9.2.0.html#font-size-and-offset-methods
                if hasattr(draw, 'textsize'):
                    text_size = draw.textsize(text=value, font=font)
                else:
                    text_size = font.getbbox(value)[2:]
                draw.rectangle([pos[0], pos[1], pos[0] + text_size[0], pos[1] + text_size[1]], fill=text_bg)
            draw.text(pos, value, font=font, fill=text_fg)
        im.save(outfile, self.image_format.upper())

def pyg_writer(code: str, filename: str):
    highlight(
        code,
        Python3Lexer(), 
        PilFormatter(
            width=600,
            height=400,
            style="lightbulb",
            line_numbers=False,
            image_pad=20,
        ),
        outfile=filename
    )

def generate_pyg_sequence(pyg_asset_dir: str, out_file: str):
    images = sorted([pyg_asset_dir + f"/{f}" for f in os.listdir(pyg_asset_dir) if f.endswith(".png")])
    clip = ImageSequenceClip.ImageSequenceClip(images, fps=5)
    clip.write_videofile(out_file)
