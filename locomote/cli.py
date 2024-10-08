import asyncio
import typer
import toml
from numpy import array as np_array
from moviepy.editor import ImageSequenceClip, CompositeVideoClip
from dacite import from_dict
from pathlib import Path
from pygments.lexers import get_lexer_by_name
from locomote.config import Cfg, DiffCfg, DiffRangeCfg, CmdCfg, RawCfg, FileCfg, ComposedCfg, LogFileCfg
from locomote.sequence import Sequence
from locomote.frame import window_img, window_ctl_img, code_img, still, CodeDisplay
from PIL import Image as PILImage
from PIL.Image import Image
from typing_extensions import Annotated

app = typer.Typer()


async def cfg_sequences(cfg: Cfg) -> list[tuple[CodeDisplay, Sequence]]:
    if isinstance(cfg.input, RawCfg):
        seq = Sequence(cfg.input.seq_start, cfg.input.seq_end, cfg.output.speed)
        display = CodeDisplay(
            font_manager=cfg.font_manager,
            token_styles=cfg.token_styles,
            line_height=cfg.line_height,
            lexer=cfg.lexer,
            style=cfg.style,
        )
        return [(display, seq)]
    elif isinstance(cfg.input, FileCfg):
        with open(cfg.input.seq_end_file) as f:
            seq_end = f.read()
        if cfg.input.seq_start_file:
            with open(cfg.input.seq_start_file) as f:
                seq_start = f.read()
        else:
            seq_start = ""
        seq = Sequence(seq_start, seq_end, cfg.output.speed)
        display = CodeDisplay(
            font_manager=cfg.font_manager,
            token_styles=cfg.token_styles,
            line_height=cfg.line_height,
            lexer=cfg.lexer,
            style=cfg.style,
        )
        return [(display, seq)]
    elif isinstance(cfg.input, CmdCfg):
        ctx = cfg.input.prompt or ""
        cmd_lexer = get_lexer_by_name("console")
        cmd_display = CodeDisplay(
            font_manager=cfg.font_manager,
            style=cfg.style,
            token_styles=cfg.token_styles,
            line_height=cfg.line_height,
            lexer=cmd_lexer,
        )
        cmd_base, _, _ = cfg.input.command.splitlines()[0].partition(" ")
        command = cfg.input.command.replace("\n\t", " \\\n\t").expandtabs(
            len(ctx + cmd_base) + 1
        )
        seq_cmd = Sequence(ctx, ctx + command)
        return [(cmd_display, seq_cmd)]
    elif isinstance(cfg.input, LogFileCfg):
        out_lexer = get_lexer_by_name("output")
        out_display = CodeDisplay(
            font_manager=cfg.font_manager,
            style=cfg.style,
            token_styles=cfg.token_styles,
            line_height=cfg.line_height,
            lexer=out_lexer,
        )
        with open(cfg.input.file) as f:
            seq_end = f.read()
        seq_log = Sequence(
            start="",
            end=seq_end,
            speed="line",
            max_line_display=cfg.input.max_lines,
            max_line_chars=cfg.max_line_chars,
        )
        return [(out_display, seq_log)]
    elif isinstance(cfg.input, DiffCfg):
        seq = Sequence(cfg.input.seq_start, cfg.input.seq_end, cfg.output.speed)
        display = CodeDisplay(
            font_manager=cfg.font_manager,
            token_styles=cfg.token_styles,
            line_height=cfg.line_height,
            lexer=cfg.lexer,
            style=cfg.style,
        )
        return [(display, seq)]
    elif isinstance(cfg.input, ComposedCfg):
        sequences = []
        for input_cfg in cfg.input.inputs:
            sequences += await cfg_sequences(Cfg(input=input_cfg, output=cfg.output))
        return sequences


async def content_blocks(
    sequences: list[tuple[CodeDisplay, Sequence]],
) -> list[list[tuple[CodeDisplay, str]]]:
    blocks = []
    stored = []
    for display, sequence in sequences:
        seq_blocks = [(display, seq) for seq in sequence]
        for sblock in seq_blocks:
            blocks.append(stored + [sblock])
        stored += [seq_blocks[-1]]
    return blocks


async def calculate_window_size(sequences: list[Sequence], cfg: Cfg) -> tuple[int, int]:
    # Width
    code_w = max([sequence.width(cfg.char_width) for sequence in sequences])
    padded_code_w = code_w + (2 * cfg.output.padding_horizontal)
    if cfg.output.width:
        width = cfg.output.width
    elif cfg.output.min_width and not cfg.output.max_width:
        width = max(padded_code_w, cfg.output.min_width)
    elif cfg.output.max_width and not cfg.output.min_width:
        width = min(padded_code_w, cfg.output.max_width)
    elif cfg.output.min_width and cfg.output.max_width:
        width = min(cfg.output.max_width, max(padded_code_w, cfg.output.min_width))
    else:
        width = padded_code_w
    # Height
    code_h = sum([sequence.height(cfg.line_height) for sequence in sequences])
    padded_code_h = code_h + (2 * cfg.output.padding_vertical)
    if cfg.output.height:
        height = cfg.output.height
    elif cfg.output.min_height and not cfg.output.max_height:
        height = max(cfg.output.min_height, padded_code_h)
    elif cfg.output.max_height and not cfg.output.min_height:
        height = min(cfg.output.max_height, padded_code_h)
    elif cfg.output.min_height and cfg.output.max_height:
        height = min(cfg.output.max_height, max(cfg.output.min_height, padded_code_h))
    else:
        height = padded_code_h
    return width, height


async def create_code_layers(window: Image, blocks_list: list[list[str]], cfg: Cfg):
    code_images = []
    if "clip" not in cfg.output.exports:
        blocks_list = [blocks_list[0], blocks_list[-1]]
    for blocks in blocks_list:
        code = await code_img(
            blocks=blocks,
            width=window.width - (cfg.output.padding_horizontal * 2),
            height=window.height - (cfg.output.padding_vertical * 2),
        )
        code_images.append(code)
    return code_images


async def exec_cfg(cfg: Cfg):
    sequences = await cfg_sequences(cfg)
    window_w, window_h = await calculate_window_size([x[1] for x in sequences], cfg)
    window = await window_img(width=window_w, height=window_h, bg_color=cfg.bg_color)
    if cfg.output.window_ctl:
        window_ctl = await window_ctl_img(window.width, cfg.default_font)
    else:
        window_ctl = None
    blocks_list = await content_blocks(sequences)
    code_layers = await create_code_layers(window, blocks_list, cfg)
    frames = [
        await still(
            window=window,
            window_ctl=window_ctl,
            code=code,
        )
        for code in code_layers
    ]
    last_frame = frames[-1]
    outpath = Path(cfg.output.path)
    if not outpath.exists():
        outpath.mkdir(parents=True)
    clip = None
    if "clip" in cfg.output.exports:
        bg_image = PILImage.new("RGBA", (last_frame.width, last_frame.height), "#71dd7c")
        clip = ImageSequenceClip(
            [np_array(img) for img in frames], 
            fps=cfg.output.fps,
        )
        bg_np = np_array(bg_image)
        bg_clip = ImageSequenceClip([bg_np for _ in frames], fps=cfg.output.fps)
        clip = CompositeVideoClip([bg_clip, clip])
        clip.write_videofile(str(outpath / f"{cfg.name}.mp4"), logger=None)
    if "still" in cfg.output.exports:
        last_frame.save(outpath / f"{cfg.name}.png")
    if "gif" in cfg.output.exports:
        if not clip:
            clip = ImageSequenceClip(
                [np_array(img) for img in frames], 
                fps=cfg.output.fps
            )
        clip.write_gif(str(outpath / f"{cfg.name}.gif"), 
                        fps=cfg.output.fps, 
                        logger=None,
                    )
    if "webm" in cfg.output.exports:
        if not clip:
            clip = ImageSequenceClip(
                [np_array(img) for img in frames], fps=cfg.output.fps
            )
        clip.write_videofile(str(outpath / f"{cfg.name}.webm"), audio=False, logger=None)


@app.command()
def run(
    inputs: Annotated[list[Path], typer.Option("-i", "--inputs", help="Input configs")],
    outputs: Annotated[
        list[Path], typer.Option("-o", "--outputs", help="Output configs")
    ],
):
    in_cfgs = {}
    out_cfgs = {}
    for inp in inputs:
        with open(inp) as f:
            in_cfgs = {**in_cfgs, **toml.load(f)}
    for out in outputs:
        with open(out) as f:
            out_cfgs = {**out_cfgs, **toml.load(f)}
    for in_key, in_cfg in in_cfgs.items():
        for out_key, out_cfg in out_cfgs.items():
            cfg_data = {"input": in_cfg, "output": out_cfg}
            cfg = from_dict(Cfg, cfg_data)
            if isinstance(cfg.input, DiffRangeCfg):
                for idx, diff_cfg in enumerate(cfg.input.diff_cfgs):
                    new_cfg = Cfg(output=cfg.output, input=diff_cfg)
                    new_cfg.name = f"{in_key}-{out_key}-{idx:03d}"
                    asyncio.run(exec_cfg(new_cfg))
            else:
                cfg.name = f"{in_key}-{out_key}"
                asyncio.run(exec_cfg(cfg))
