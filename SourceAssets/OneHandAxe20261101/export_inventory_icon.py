"""Rebuild this inventory PNG through the existing UE catalog-image pipeline."""
from pathlib import Path
import os
import shutil
import subprocess

P=Path(__file__).resolve().parent
project=P.parents[1]
# Asset rendering uses the already-built editor; avoid waiting for an unrelated
# native build merely to rerun startup SDK discovery (UE's supported switch).
environment=os.environ.copy()
environment['UE_SKIP_UBT_SDK_SETUP']='1'
subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',
    str(project/'Tools/UI/build_weapon_catalog_icons.ps1'),
    '-Definitions','ue_tactical_hatchet'],check=True,env=environment)
shutil.copy2(project/'Content/ColdSteelData/Icons/ue_tactical_hatchet.png',
             P/'Icons/ue_tactical_hatchet.png')
