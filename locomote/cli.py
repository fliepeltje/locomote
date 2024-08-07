import typer
import toml
import asyncio
from PIL.Image import Image
from dacite import from_dict
from pathlib import Path
from locomote.config import Cfg, RawCfg, FileCfg
from locomote.draw.code import LoC
from locomote.sequence import Sequence
from locomote.assets import initialize_base_still, create_still, create_clip


from typing_extensions import Annotated, AsyncIterator, Literal

app = typer.Typer()

async def exec_cfg(cfg: Cfg):
    if isinstance(cfg.input, RawCfg):
        sequence = Sequence(cfg.input.seq_start, cfg.input.seq_end, cfg.output.speed)
    elif isinstance(cfg.input, FileCfg):
        with open(cfg.input.seq_end_file) as f:
            seq_end = f.read()
        if cfg.input.seq_start_file:
            with open(cfg.input.seq_start_file) as f:
                seq_start = f.read()
        else:
            seq_start = ""
        sequence = Sequence(seq_start, seq_end, cfg.output.speed)
    code_w, code_h = sequence.width(cfg), sequence.height(cfg)
    base_img = await initialize_base_still(cfg, code_w, code_h)
    locs = [LoC(x, cfg) for x in sequence]
    images = [await create_still(base_img, loc) for loc in locs]
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
