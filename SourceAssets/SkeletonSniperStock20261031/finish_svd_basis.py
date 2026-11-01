"""Use UE's built-in tangent solver for the SVD connector's narrow faces."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/SkeletonSniperStock20261031/Meshes/SM_SniperSkeleton_SVD')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for i in range(sub.get_lod_count(mesh)):
    settings=sub.get_lod_build_settings(mesh,i)
    settings.recompute_tangents=True;settings.use_mikk_t_space=False
    sub.set_lod_build_settings(mesh,i,settings)
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('SVD tangent basis not saved')
(O/'svd_basis_receipt.json').write_text(json.dumps(dict(saved=True,path=mesh.get_path_name(),solver='Unreal built-in',native_fit_unchanged=True),indent=2))
print('SVD_BUILTIN_TANGENT_BASIS_SAVED')
