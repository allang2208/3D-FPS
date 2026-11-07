from pathlib import Path
import unreal as u
base="/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_"
for kind in ("Native","Advanced"):
    a=u.load_asset(base+kind)
    print(kind,a.get_path_name(),[(str(m.material_slot_name),m.material_interface.get_name() if m.material_interface else None) for m in a.static_materials])
