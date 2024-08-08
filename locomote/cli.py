import typer
import toml
import asyncio
from dacite import from_dict
from pathlib import Path
from pygments.lexers import get_lexer_by_name
from locomote.config import Cfg, DiffCfg, DiffRangeCfg, CmdCfg, RawCfg, FileCfg
from locomote.draw.code import LoC
from locomote.sequence import Sequence
from locomote.assets import initialize_base_still, create_still, create_clip


from typing_extensions import Annotated

app = typer.Typer()


async def cfg_sequences(cfg: Cfg) -> list[Sequence]:
    if isinstance(cfg.input, RawCfg):
        return [
            Sequence(
                cfg.input.seq_start, cfg.input.seq_end, cfg.lexer, cfg.output.speed
            )
        ]
    elif isinstance(cfg.input, FileCfg):
        with open(cfg.input.seq_end_file) as f:
            seq_end = f.read()
        if cfg.input.seq_start_file:
            with open(cfg.input.seq_start_file) as f:
                seq_start = f.read()
        else:
            seq_start = ""
        return [Sequence(seq_start, seq_end, cfg.lexer, cfg.output.speed)]
    elif isinstance(cfg.input, CmdCfg):
        ctx = cfg.input.prompt or ""
        cmd_lexer = get_lexer_by_name("console")
        out_lexer = get_lexer_by_name("output")
        cmd_base, _, _ = cfg.input.command.splitlines()[0].partition(" ")
        command = cfg.input.command.replace("\n\t", " \\\n\t").expandtabs(
            len(ctx + cmd_base) + 1
        )
        seq_cmd = Sequence(ctx, ctx + command, cmd_lexer, "token", None)
        if not cfg.input.logfile:
            return [seq_cmd]
        with open(cfg.input.logfile) as f:
            seq_end = f.read()
        seq_log = Sequence("", seq_end, out_lexer, "line", cfg.output.max_line_display)
        return [seq_cmd, seq_log]
    elif isinstance(cfg.input, DiffCfg):
        return [
            Sequence(
                cfg.input.seq_start, cfg.input.seq_end, cfg.lexer, cfg.output.speed
            )
        ]


async def code_box(cfg: Cfg, sequences: list[Sequence]) -> tuple[int, int]:
    code_w = max([sequence.width(cfg) for sequence in sequences])
    code_h = sum([sequence.height(cfg) for sequence in sequences])
    return code_w, code_h


async def locs_from_sequences(cfg: Cfg, sequences: list[Sequence]) -> list[list[LoC]]:
    locs_arrays = []
    offset = 0
    stored = []
    for sequence in sequences:
        seq_locs = [LoC(seq, cfg, sequence.lexer, offset) for seq in sequence]
        for loc in seq_locs:
            locs_arrays.append(stored + [loc])
        stored.append(seq_locs[-1])
        offset += sequence.height(cfg)
    return locs_arrays


async def exec_cfg(cfg: Cfg):
    sequences = await cfg_sequences(cfg)
    code_w, code_h = await code_box(cfg, sequences)
    base_img = await initialize_base_still(cfg, code_w, code_h)
    locs = await locs_from_sequences(cfg, sequences)
    images = [await create_still(base_img, loclist) for loclist in locs]
    outpath = Path(cfg.output.path)
    if not outpath.exists():
        outpath.mkdir(parents=True)
    if "stills" in cfg.output.exports:
        start, end = images[0], images[-1]
        start.save(outpath / f"{cfg.name}-start.png")
        end.save(outpath / f"{cfg.name}-end.png")
    if "clip" in cfg.output.exports:
        clip = await create_clip(images, cfg.output.fps)
        clip.write_videofile(str(outpath / f"{cfg.name}.mp4"), logger=None)


async def exec_parallel(cfgs: list[Cfg]):
    async with asyncio.TaskGroup() as tg:
        for cfg in cfgs:
            tg.create_task(exec_cfg(cfg))


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
    tasks = []
    for in_cfg in inputs:
        for out_cfg in outputs:
            cfg_data = {"input": cfg_dict[in_cfg], "output": cfg_dict[out_cfg]}
            cfg = from_dict(Cfg, cfg_data)
            if isinstance(cfg.input, DiffRangeCfg):
                for idx, diff_cfg in enumerate(cfg.input.diff_cfgs):
                    new_cfg = Cfg(output=cfg.output, input=diff_cfg)
                    new_cfg.name = f"{in_cfg}-{out_cfg}-{idx:03d}"
                    tasks.append(new_cfg)
            else:
                cfg.name = f"{in_cfg}-{out_cfg}"
                tasks.append(cfg)

    asyncio.run(exec_parallel(tasks))
