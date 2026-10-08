import runpy
from pathlib import Path
P=Path(__file__).resolve().parent
runpy.run_path(str(P/'install_assets.py'),run_name='xuanchi_rune_guard_install')
runpy.run_path(str(P/'install_shared_icons.py'),run_name='xuanchi_rune_guard_icon_install')
