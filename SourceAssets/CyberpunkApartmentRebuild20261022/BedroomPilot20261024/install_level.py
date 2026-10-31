"""Production bedroom installation; the standalone sample map is retired."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parent
def apply_upgrade(world):
    return runpy.run_path(str(ROOT/'Integration20261024/install_level.py'))['apply_upgrade'](world)
def main():
    return runpy.run_path(str(ROOT/'Integration20261024/install_level.py'))['main']()
if __name__=='__main__':main()
