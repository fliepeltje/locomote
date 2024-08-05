import os

os.makedirs(".output", exist_ok=False)

for f in os.listdir(".tmp"):
    print(f)