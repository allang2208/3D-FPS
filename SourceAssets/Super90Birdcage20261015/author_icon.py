"""Restore the current framed icon; the simplified Blender frame is retired.
When model geometry changes, regenerate through the documented imagegen workflow.
"""
from pathlib import Path
import shutil
O=Path(__file__).parent
source=O.parent/'ShotgunIconsFramed20261015/Final/muzzle_shotgun_birdcage_flash_hider.png'
shutil.copy2(source,O/'muzzle_shotgun_birdcage_flash_hider.png')
print('CURRENT_FRAMED_SHOTGUN_ICON_RESTORED')
