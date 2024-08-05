import os
from shutil import rmtree
from pathlib import Path
from typer import Typer, Option
from locomote.config import Config
from locomote.utils import generate_text_iter, FileHistory, exec_config
from typing import Optional
from typing_extensions import Annotated

app = Typer()


@app.command()
def config(cfg_path: Path, key: str):
    cfg = Config.from_toml(cfg_path)[key]
    exec_config(cfg)


if __name__ == "__main__":
    app()
