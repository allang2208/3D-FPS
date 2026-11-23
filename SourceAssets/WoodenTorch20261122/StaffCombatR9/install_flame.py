"""Increase the upper flame sway on the R8 torch and carry the motion into its distant emitter."""
import json
import os
import sys
from pathlib import Path
import unreal as u
project = Path(os.environ["FPS_PROJECT_ROOT"])
source = project/"SourceAssets/WoodenTorch20261122/StaffCombatR9"
old = "/Game/Weapons/WoodenTorch20261122/FlameReviewR8/"
new = "/Game/Weapons/WoodenTorch20261122/StaffCombatR9/"
lib = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
def fork(name):
    path = new+name
    obj = lib.load_asset(path) if lib.does_asset_exist(path) else lib.duplicate_asset(old+name,path)
    if not obj:
        raise RuntimeError(path)
    return obj
def save(obj):
    if not lib.save_loaded_asset(obj,False):
        raise RuntimeError(obj.get_path_name())
mat = fork("M_HearthFlameVolume")
field, = [n for n in edit.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom)]
field.set_editor_property("code",(source/"HearthFlame.hlsl").read_text(encoding="utf8"))
edit.recompile_material(mat)
save(mat)
mesh = fork("SM_HearthFlameVolume")
mesh.set_material(0,mat)
save(mesh)
sys.path.insert(0,str(project/"Tools/Skills"))
from build_fireball_assets import assignments
system=fork("NS_HearthWrap")
phase="frac(float(Particles.UniqueID)*.61803399)"
angle=f"(6.2831853*{phase})"
up="float3(Engine.Owner.SystemXAxis.z,Engine.Owner.SystemYAxis.z,Engine.Owner.SystemZAxis.z)"
# Advect each distant tongue upwards with a small independent sideways impulse.
assignments(system,"Fire","ParticleSpawnScript",{
    "Particles.Velocity":("/Script/CoreUObject.Vector3f",f"{up}*8.0+float3(4.6*cos({angle}),4.6*sin({angle}),0)")})
if not u.RainAssetEditor.compile_rain(system,True):
    raise RuntimeError("Distant torch emitter did not compile")
save(system)
Path(os.environ["TORCH_BATCH"],"assets.json").write_text(json.dumps({"saved":[mat.get_path_name(),mesh.get_path_name(),system.get_path_name()],"slot":mesh.get_material(0).get_path_name()},indent=2))
