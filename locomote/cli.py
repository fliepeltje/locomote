import typer
import toml
import asyncio
from dacite import from_dict
from pathlib import Path
from pygments.lexers import get_lexer_by_name
from locomote.config import Cfg, CmdCfg, RawCfg, FileCfg
from locomote.draw.code import LoC
from locomote.sequence import Sequence
from locomote.assets import initialize_base_still, create_still, create_clip


from typing_extensions import Annotated

app = typer.Typer()

async def cfg_sequences(cfg: Cfg) -> list[Sequence]:
    if isinstance(cfg.input, RawCfg):
        return [
            Sequence(cfg.input.seq_start, cfg.input.seq_end, cfg.lexer, cfg.output.speed)
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
        ctx = cfg.input.host_ctx or ""
        with open(cfg.input.logfile) as f:
            seq_end = f.read()
        bash_lexer = get_lexer_by_name("bash")
        out_lexer = get_lexer_by_name("output")
        seq_cmd = Sequence(ctx, ctx + cfg.input.command + "\n", bash_lexer, "token")
        seq_log = Sequence("", seq_end, out_lexer, "line")
        return [seq_cmd, seq_log]
    
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
    cfg_path: Path,
    inputs: Annotated[list[str], typer.Option("-i", "--inputs", help="Input configs")],
    outputs: Annotated[
        list[str], typer.Option("-o", "--outputs", help="Output configs")
    ],
):
    with open(cfg_path) as f:
        cfg_dict = toml.load(f)
    tasks = []
    for in_cfg in inputs:
        for out_cfg in outputs:
            cfg_data = {"input": cfg_dict[in_cfg], "output": cfg_dict[out_cfg]}
            cfg = from_dict(Cfg, cfg_data)
            cfg.name = f"{in_cfg}-to-{out_cfg}"
            tasks.append(cfg)

            # asyncio.run(exec_cfg(cfg, key))

    asyncio.run(exec_parallel(tasks))
