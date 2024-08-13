import asyncio
import typer
import toml
from numpy import array as np_array
from moviepy.editor import ImageSequenceClip
from dacite import from_dict
from pathlib import Path
from pygments.lexers import get_lexer_by_name
from locomote.config import Cfg, DiffCfg, DiffRangeCfg, CmdCfg, RawCfg, FileCfg, ComposedCfg, LogFileCfg
from locomote.sequence import Sequence
from locomote.frame import window_img, window_ctl_img, code_img, still, CodeDisplay
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
    outpath = Path(cfg.output.path)
    if not outpath.exists():
        outpath.mkdir(parents=True)
    clip = None
    if "clip" in cfg.output.exports:
        clip = ImageSequenceClip([np_array(img) for img in frames], fps=cfg.output.fps)
        clip.write_videofile(str(outpath / f"{cfg.name}.mp4"), logger=None)
    if "still" in cfg.output.exports:
        frames[-1].save(outpath / f"{cfg.name}.png")
    if "gif" in cfg.output.exports:
        if not clip:
            clip = ImageSequenceClip(
                [np_array(img) for img in frames], fps=cfg.output.fps
            )
        clip.write_gif(str(outpath / f"{cfg.name}.gif"), logger=None)


@app.command()
def run(
    cfg_paths: list[Path],
    inputs: Annotated[list[str], typer.Option("-i", "--inputs", help="Input configs")],
    outputs: Annotated[
        list[str], typer.Option("-o", "--outputs", help="Output configs")
    ],
):
    cfg_dict = {}
    for cfg_path in cfg_paths:
        with open(cfg_path) as f:
            cfg_d = toml.load(f)
        for key, val in cfg_d.items():
            cfg_dict[key] = {**cfg_dict.get(key, {}), **val}
    for in_cfg in inputs:
        for out_cfg in outputs:
            cfg_data = {"input": cfg_dict[in_cfg], "output": cfg_dict[out_cfg]}
            cfg = from_dict(Cfg, cfg_data)
            if isinstance(cfg.input, DiffRangeCfg):
                for idx, diff_cfg in enumerate(cfg.input.diff_cfgs):
                    new_cfg = Cfg(output=cfg.output, input=diff_cfg)
                    new_cfg.name = f"{in_cfg}-{out_cfg}-{idx:03d}"
                    asyncio.run(exec_cfg(new_cfg))
            else:
                cfg.name = f"{in_cfg}-{out_cfg}"
                asyncio.run(exec_cfg(cfg))
