import os
from pathlib import Path

path = Path(".output")
os.makedirs(str(path), exist_ok=True)

for f in os.listdir(".tmp"):
    print(f)