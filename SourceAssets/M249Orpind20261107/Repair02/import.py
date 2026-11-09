"""Publish only the M249 mesh, materials, component meshes and native clips."""
from pathlib import Path
import unreal as u

root=Path(__file__).resolve().parents[1]
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
       if p.get_path_name().startswith("/Game/Weapons/M249/")]
if dirty:
    raise RuntimeError("Preserve unsaved M249 packages "+str(dirty))
for name in ("import_assets.py","import_motion.py"):
    script=root/name
    exec(compile(script.read_text(encoding="utf8"),str(script),"exec"),
         {"__file__":str(script),"__name__":"__main__"})
print("M249_REPAIR02_SAVED",flush=True)
