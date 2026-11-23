"""Rebuild only the R8 material and its render proxy from the shipped R7 graph."""
import json
import os
import sys
from pathlib import Path
import unreal as u
project = Path(os.environ["FPS_PROJECT_ROOT"])
source = project/"SourceAssets/WoodenTorch20261122/FlameReviewR8"
old = "/Game/Weapons/WoodenTorch20261122/HearthWrapR7/"
new = "/Game/Weapons/WoodenTorch20261122/FlameReviewR8/"
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
# Keep the six-per-second emitter and its original flipbook. Lift and widen just the distant flame.
assignments(system,"Fire","ParticleSpawnScript",{
    "Particles.Position":("/Script/Niagara.NiagaraPosition",f"float3(1.8*cos({angle}),1.8*sin({angle}),7.)+{up}*9.0"),
    "Particles.SpriteSize":("/Script/CoreUObject.Vector2f",f"float2(lerp(15.,19.,{phase}),lerp(32.,40.,{phase}))")})
if not u.RainAssetEditor.compile_rain(system,True):
    raise RuntimeError("Distant torch emitter did not compile")
save(system)
Path(os.environ["TORCH_BATCH"],"r8-assets.json").write_text(json.dumps({"saved":[mat.get_path_name(),mesh.get_path_name(),system.get_path_name()],"slot":mesh.get_material(0).get_path_name()},indent=2))
