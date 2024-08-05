import logging
from shutil import rmtree
from dataclasses import dataclass
from git import Repo, Commit
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments import highlight
from locomote.config import Config, DiffConfig, CmdConfig, FileConfig
from locomote.writer import CodeBlockFormatter
from moviepy.video.io import ImageSequenceClip
from locomote.parser import Segment
from pathlib import Path

from typing import Iterator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_text_iter(from_text: str, to_text: str) -> Iterator[str]:
    yield from_text
    segments = Segment.from_sequences(from_text, to_text)
    text_modifiers = []
    for seg in segments:
        text_modifiers += seg.token_mods()
    for mod in text_modifiers:
        from_text = mod(from_text)
        yield from_text
    yield to_text



def generate_cmd_iter(
        cmd: str, 
        cmd_log: str, 
        line_display: int = 15,
        host_line: str | None = None
    ):
    seq_a = f"{host_line} " if host_line else ""
    seq_b = f"{host_line} {cmd}" if host_line else cmd
    yield seq_a
    yield from generate_text_iter(seq_a, seq_b)
    prefix = seq_b + "\n\n"
    yield prefix
    content = []
    for line in cmd_log.split("\n"):
        content.append(line)
        text = "\n".join(content[-line_display:])
        yield prefix + text
    yield prefix +  "\n".join(content[-line_display:])


@dataclass
class FileHistory:
    path: Path
    commits: list[Commit]

    @classmethod
    def from_repo(
        cls, file_path: str, repo_dir: str | None = None, rev: str | None = None
    ) -> "FileHistory":
        repo = Repo(repo_dir) if repo_dir else Repo(".")
        return cls(
            Path(file_path),
            sorted(
                [x for x in repo.iter_commits(rev=rev, paths=file_path)],
                key=lambda x: x.committed_datetime,
            ),
        )

    def content_for(self, commit: Commit) -> str:
        return commit.tree[str(self.path)].data_stream.read().decode()

    @property
    def sequence_iter(self) -> Iterator[tuple[Commit, Iterator[str]]]:
        for idx in range(1, len(self.commits)):
            yield (
                self.commits[idx],
                generate_text_iter(
                    self.content_for(self.commits[idx - 1]),
                    self.content_for(self.commits[idx]),
                ),
            )


def formatter_from_cfg(cfg: Config) -> CodeBlockFormatter:
    match cfg.output.type:
        case "code-block":
            return CodeBlockFormatter(
                width=cfg.output.pil.width,
                height=cfg.output.pil.height,
                style=cfg.output.pil.style,
                line_numbers=False,
                image_pad=cfg.output.pil.image_pad,
                font_name=cfg.output.pil.font_name,
                filename=cfg.input.file,
            )
        case _:
            raise ValueError(f"Unsupported output type: {cfg.output.type}")


def create_temporary_assets(tmp_dir: Path, seq_iter: Iterator[str], cfg: Config):
    logger.info(f"Creating temporary assets in {tmp_dir}")
    if not tmp_dir.exists():
        tmp_dir.mkdir(parents=True)
    lex = (
        get_lexer_by_name(cfg.input.lang)
        if cfg.input.lang
        else get_lexer_for_filename(cfg.input.file)
    )
    for idx, text in enumerate(seq_iter):
        png_out = tmp_dir / f"{(idx):06d}.png"
        highlight(text, lex, formatter_from_cfg(cfg), str(png_out))


def process_output(cfg: Config, pngs: list[Path], out: Path, prefix: str = ""):
    assets = sorted(pngs)
    if cfg.output.assets.clip:
        logger.info(f"Creating clip")
        clip_out = out / f"{prefix}-clip.mp4" if prefix else out / "clip.mp4"
        clip = ImageSequenceClip.ImageSequenceClip([str(x) for x in assets], fps=12)
        clip.write_videofile(str(clip_out), logger=None)
    if cfg.output.assets.head_img:
        logger.info(f"Creating head image")
        assets[0].rename(out / f"{prefix}-head.png" if prefix else out / "head.png")
    if cfg.output.assets.tail_img:
        logger.info(f"Creating tail image")
        assets[-1].rename(out / f"{prefix}-tail.png" if prefix else out / "tail.png")
    


def exec_config(cfg: Config):
    outpath = Path(cfg.output.path)
    if not outpath.exists():
        outpath.mkdir(parents=True)
    if isinstance(cfg.input, DiffConfig):
        logger.info(f"Found diff config")
        history = FileHistory.from_repo(
            cfg.diff.file, repo_dir=cfg.diff.repo, rev=cfg.diff.rev
        )
        for commit_idx, (commit, seq_iter) in enumerate(history.sequence_iter):
            clip_id = f"{commit_idx:03d}-" + commit.summary.replace(" ", "-").lower()
            tmp_dir = outpath / clip_id
            create_temporary_assets(tmp_dir, seq_iter, cfg)
            pngs = [x for x in tmp_dir.iterdir() if x.suffix == ".png"]
            process_output(cfg, pngs, outpath, prefix=clip_id)
            rmtree(tmp_dir)
    elif isinstance(cfg.input, FileConfig):
        logger.info(f"Found file config")
        if cfg.file.src:
            with open(cfg.file.src, "r") as f:
                seq_a = f.read()
        else:
            seq_a = ""
        with open(cfg.file.dst, "r") as f:
            seq_b = f.read()
        tmp_dir = outpath / ".tmp"
        create_temporary_assets(tmp_dir, generate_text_iter(seq_a, seq_b), cfg)
        pngs = [x for x in tmp_dir.iterdir() if x.suffix == ".png"]
        process_output(cfg, pngs, outpath)
        rmtree(tmp_dir)
    elif isinstance(cfg.input, CmdConfig):
        logger.info(f"Found cmd config")
        with open(cfg.cmd.logfile, "r") as f:
            cmd_log = f.read()
        seq_iter = generate_cmd_iter(cfg.cmd.cmd, cmd_log, cfg.cmd.logline_display, cfg.cmd.host_line)
        tmp_dir = outpath / ".tmp"
        create_temporary_assets(tmp_dir, seq_iter, cfg)
        pngs = [x for x in tmp_dir.iterdir() if x.suffix == ".png"]
        process_output(cfg, pngs, outpath)
        rmtree(tmp_dir)