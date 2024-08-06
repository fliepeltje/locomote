import typer
import toml
import asyncio
from dataclasses import dataclass
from PIL.Image import Image
from moviepy.editor import ImageSequenceClip
from dacite import from_dict
from pathlib import Path
from locomote.config import Cfg, InputCfg, OutputCfg, RawCfg, DiffCfg, CmdCfg, FileCfg
from locomote.img import Stills
from locomote.parser import generate_text_iter
from locomote.clip import create_clip_from_images

from typing_extensions import Annotated, AsyncIterator, Literal

app = typer.Typer()


@dataclass
class Assets:
    key: str
    stills: tuple[Image, Image] | None
    clip: ImageSequenceClip | None

    @classmethod
    async def create(
        cls,
        key: str,
        seq_iter: AsyncIterator[str],
        stills: Stills,
        exports: list[Literal["stills", "clip"]],
    ):
        tasks = []
        base_img, base_draw = await stills.init_image()
        await stills.draw_window(base_draw)
        await stills.draw_window_ctl(base_draw)
        async with asyncio.TaskGroup() as tg:
            async for text in seq_iter:
                tasks.append(tg.create_task(stills.create_still(base_img, text)))
        all_stills = [task.result() for task in tasks]
        clip_stills = (all_stills[0], all_stills[-1]) if "stills" in exports else None
        clip = await create_clip_from_images(all_stills) if "clip" in exports else None
        return cls(key, clip_stills, clip)

    async def store(self, outpath: str):
        if not Path(outpath).exists():
            Path(outpath).mkdir(parents=True)
        if self.stills:
            self.stills[0].save(f"{outpath}/{self.key}-start.png")
            self.stills[1].save(f"{outpath}/{self.key}-end.png")
        if self.clip:
            self.clip.write_videofile(f"{outpath}/{self.key}.mp4", logger=None)


async def exec_cfg(
    stills: Stills, input_cfg: InputCfg, output_cfg: OutputCfg, key: str
) -> Assets:
    if isinstance(input_cfg.cfg, RawCfg):
        seq_iter = generate_text_iter(input_cfg.cfg.seq_start, input_cfg.cfg.seq_end)
        assets = await Assets.create(key, seq_iter, stills, output_cfg.exports)
        await assets.store(output_cfg.path)
    elif isinstance(input_cfg.cfg, FileCfg):
        new_input = InputCfg(lang=input_cfg.lang, cfg=input_cfg.cfg.raw)
        await exec_cfg(stills, new_input, output_cfg, key)
    elif isinstance(input_cfg.cfg, DiffCfg):
        for idx, (commit, raw) in enumerate(input_cfg.cfg.raw):
            new_input = InputCfg(lang=input_cfg.lang, cfg=raw)
            commit_summary = commit.summary.replace(" ", "-").lower()
            commit_key = f"{key}-{idx:03d}-{commit_summary}"
            await exec_cfg(new_input, output_cfg, commit_key)
    elif isinstance(input_cfg.cfg, CmdCfg):
        cmd_raw, log_raw = input_cfg.cfg.raw
        await exec_cfg(stills, InputCfg(lang=input_cfg.lang, cfg=cmd_raw), output_cfg, key)
        seq_iter = generate_text_iter(log_raw.seq_start, log_raw.seq_end, speed="newlines")
        assets = await Assets.create(f"{key}-cmd", seq_iter, stills, output_cfg.exports)
        await assets.store(output_cfg.path)


async def exec_parallel(cfgs: dict[str, Cfg]):
    async with asyncio.TaskGroup() as tg:
        for key, cfg in cfgs.items():
            stills = Stills(cfg.input, cfg.output)
            tg.create_task(exec_cfg(stills, cfg.input, cfg.output, key))


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
    tasks = {}
    for in_cfg in inputs:
        for out_cfg in outputs:
            key = f"{in_cfg}-to-{out_cfg}"
            cfg = Cfg(
                from_dict(data_class=InputCfg, data=cfg_dict[in_cfg]),
                from_dict(data_class=OutputCfg, data=cfg_dict[out_cfg]),
            )
            tasks[key] = cfg
            # asyncio.run(exec_cfg(cfg, key))

    asyncio.run(exec_parallel(tasks))
