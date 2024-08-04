import os
from shutil import rmtree
from pathlib import Path
from typer import Typer
from locomote.utils import generate_text_iter
from locomote.writer import pyg_writer, generate_pyg_sequence

app = Typer()

@app.command()
def file(
        src: Path, 
        dst: Path,
        output: Path = ".output/out.mp4"
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
        pyg_writer(text, png_out)
    generate_pyg_sequence(".tmp", str(output))
    rmtree(".tmp")



@app.command()
def diff():
    pass

if __name__ == "__main__":
    app()