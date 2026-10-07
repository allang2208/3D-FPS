"""Restore the live Azure Dragon V10 assets in dependency order (V9 retired 2026-10-07)."""
import runpy
from pathlib import Path
root=Path(__file__).resolve().parent
for script in ('install_ue.py',                  # shared Fab normal atlas
               'ClawV10/install_textures_ue.py',  # claw vein / smoke reference textures
               'HudV10/install_hud_ue.py',        # screen-space energy HUD
               'ClawV10/install_fab_ue.py'):      # Fab claw mesh, rig, gesture and all claw materials
    runpy.run_path(str(root/script),run_name='__main__')
