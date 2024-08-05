from PIL import Image, ImageDraw

from pygments.formatters import ImageFormatter


class CodeBlockFormatter(ImageFormatter):
    def __init__(
        self,
        width: int,
        height: int,
        padding: int = 10,
        filename: str | None = None,
        window_control: bool = True,
        **options,
    ):
        super().__init__(**options)
        self.width = width
        self.height = height
        self.padding = padding
        self.filename = filename
        self.window_control = window_control

    def _draw_code_highlights(self, draw: ImageDraw):
        if self.hl_lines:
            x = self.image_pad + self.line_number_width - self.line_number_pad + 1
            recth = self._get_line_height()
            rectw = self.width - x
            for linenumber in self.hl_lines:
                y = self._get_line_y(linenumber - 1)
                draw.rectangle([(x, y), (x + rectw, y + recth)], fill=self.hl_color)

    def _draw_code_box(self, draw: ImageDraw):
        draw.rounded_rectangle(
            [(0, 0), (self.width, self.height)], fill=self.background_color, radius=10
        )

    def _draw_code(self, draw: ImageDraw):
        for pos, value, font, text_fg, text_bg in self.drawables:
            if text_bg:
                # see deprecations https://pillow.readthedocs.io/en/stable/releasenotes/9.2.0.html#font-size-and-offset-methods
                if hasattr(draw, "textsize"):
                    text_size = draw.textsize(text=value, font=font)
                else:
                    text_size = font.getbbox(value)[2:]
                draw.rectangle(
                    [pos[0], pos[1], pos[0] + text_size[0], pos[1] + text_size[1]],
                    fill=text_bg,
                )
            draw.text(pos, value, font=font, fill=text_fg)

    def _draw_filename(self, draw: ImageDraw):
        if self.filename:
            font = self.fonts.get_font(False, False)
            text_width = font.getbbox(self.filename)[2]

            text_x = (self.width - text_width) // 2
            text_y = 10
            draw.text(
                (text_x, text_y),
                self.filename,
                font=font,
                fill=(128, 128, 128),  # Use RGB values for grey color
            )

    def _draw_window_ctl(self, draw: ImageDraw):
        if self.window_control:
            draw.ellipse(
                [(10, 10), (20, 20)],
                fill="#FF605C",  # Use RGB values for red color
            )
            draw.ellipse(
                [(25, 10), (35, 20)],
                fill="#FFBD44",  # Use RGB values for yellow color
            )
            draw.ellipse(
                [(40, 10), (50, 20)],
                fill="#00CA4E",  # Use RGB values for green color
            )
            draw.line([(0, 35), (self.width, 35)], fill=(128, 128, 128, 50))

    def format(self, tokensource, outfile):
        self._create_drawables(tokensource)
        self._draw_line_numbers()
        im = Image.new(
            "RGB",
            (self.width, self.height),
            (0, 0, 0, 0),
        )

        self._paint_line_number_bg(im)
        draw = ImageDraw.Draw(im)
        self._draw_code_box(draw)
        self._draw_window_ctl(draw)
        self._draw_filename(draw)
        self._draw_code_highlights(draw)
        self._draw_code(draw)

        im.save(outfile, self.image_format.upper())
