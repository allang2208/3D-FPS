"""Rebuild the two authored static poses with explicit tangent/UV precision."""
import json
from pathlib import Path
import unreal as u

HERE=Path(__file__).parent
ROOT='/Game/Props/GamedevTreasureChest20260922/'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Static mesh editing requires PIE to finish first.')
subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved=[]
for name in ('SM_TreasureChest_Closed','SM_TreasureChest_Open'):
    mesh=u.load_asset(ROOT+name)
    build=subsystem.get_lod_build_settings(mesh,0)
    build.recompute_tangents=True
    build.use_mikk_t_space=True
    build.use_high_precision_tangent_basis=True
    build.use_full_precision_u_vs=True
    subsystem.set_lod_build_settings(mesh,0,build)
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(ROOT+name)],False):
        raise RuntimeError('Cannot save '+name)
    saved.append(mesh.get_path_name())
receipt=dict(saved=saved,recompute_tangents=True,mikk_t_space=True,
             high_precision_tangent_basis=True,full_precision_uvs=True,tested=False)
(HERE/'static_build_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TREASURE_STATIC_BUILD_SAVED '+json.dumps(receipt))
