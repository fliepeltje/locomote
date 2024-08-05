from pathlib import Path
from typer import Typer
from locomote.config import Config
from locomote.utils import exec_config

app = Typer()


@app.command()
def config(cfg_path: Path, key: str):
    cfg = Config.from_toml(cfg_path)[key]
    exec_config(cfg)

if __name__ == "__main__":
    app()