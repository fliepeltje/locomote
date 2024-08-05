import os
from shutil import rmtree
from pathlib import Path
from typer import Typer, Option
from locomote.utils import generate_text_iter, FileHistory
from locomote.writer import pyg_writer, generate_pyg_sequence

from typing import Optional
from typing_extensions import Annotated

app = Typer()

@app.command()
def file(
        src: Path, 
        dst: Path,
        output: Annotated[
            Path, 
            Option("--output", "-o", help="Output file path")
        ] = Path(".output/out.mp4"),
        src_filename: Annotated[
            Optional[str], 
            Option("--src-name", help="Source filename (appears at top of window control)")
        ] = None,
        src_lang: Annotated[
            Optional[str], 
            Option("--lang", help="Source language (used as lexer)")
        ] = None,
    ):
    with open(src, "r") as f:
        seq_a = f.read()
    with open(dst, "r") as f:
        seq_b = f.read()
    if not os.path.exists(".tmp"):
        os.makedirs(".tmp")
    for idx, text in enumerate(generate_text_iter(seq_a, seq_b)):
        asset_nr = f"{(idx):06d}"
        png_out = f".tmp/{asset_nr}.png"
        pyg_writer(text, png_out, src_filename, src_lang)
    generate_pyg_sequence(".tmp", str(output))
    rmtree(".tmp")


@app.command()
def diff(
    file: Path,
    output_dir: Annotated[
        Path,
        Option("--output", "-o", help="Output directory")
    ],
    rev: Annotated[
        Optional[str],
        Option("--rev", help="Revision to compare against")
    ] = None,
    repo_dir: Annotated[
        Optional[str],
        Option("--repo", help="Path to repository")
    ] = None,
):
    history = FileHistory.from_repo(file, repo_dir=repo_dir, rev=rev)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for commit_idx, (commit, seq_iter) in enumerate(history.sequence_iter):
        base_name = f"{commit_idx:03d}-" +  commit.summary.replace(" ", "-").lower()
        clip_out = f"{output_dir}/{base_name}.mp4"
        clip_temp = f"{output_dir}/.{base_name}-tmp"
        if not os.path.exists(clip_temp):
            os.makedirs(clip_temp)
        for idx, text in enumerate(seq_iter):
            asset_nr = f"{(idx):06d}"
            png_out = f"{clip_temp}/{asset_nr}.png"
            pyg_writer(text, png_out, filename=str(file))
        generate_pyg_sequence(clip_temp, clip_out)
        rmtree(clip_temp)

if __name__ == "__main__":
    app()