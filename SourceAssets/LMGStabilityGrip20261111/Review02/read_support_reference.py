"""Read the existing SVD support pose; do not edit current UE assets."""
import ast,json,unreal as u
from pathlib import Path
HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE.parent/'collect.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'read-helpers','exec'))
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
dm,_=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);bones=sorted(bones,key=lambda b:b.index);names=[str(b.name) for b in bones]
a=u.load_asset('/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_idle')
result=dict(mesh=mesh.get_path_name(),names=names,parents=[b.parent_index for b in bones],bind=[tr(b.world_transform) for b in bones],idle=a.get_path_name(),local=[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,0.,False,mesh)],profile=profile('/Game/Weapons/SVDDragunov20260922/GripProfiles20261001/DA_SVD_Grip_base'))
(HERE/'svd_reference.json').write_text(json.dumps(result));print('Saved existing SVD support pose reference; no asset writes.')
