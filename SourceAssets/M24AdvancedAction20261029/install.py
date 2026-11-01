"""Active M24 front chassis: FullBodyV3."""
import runpy,shutil
from pathlib import Path
O=Path(__file__).resolve().parent
runpy.run_path(str(O/"FullBodyV3/install.py"),run_name="__main__")
shutil.copy2(O/"FullBodyV3/install_receipt.json",O/"install_receipt.json")
