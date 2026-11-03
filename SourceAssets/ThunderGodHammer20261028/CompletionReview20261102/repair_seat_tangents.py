"""Repair saved Thor seat tangent bases without changing source geometry."""
import unreal as u
import json,shutil,datetime
from pathlib import Path
P=Path(__file__).resolve().parent
R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
backup=P/'AssetBackups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True,exist_ok=True)
subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
rows=[]
for asset_path in (
    '/Game/Weapons/ThunderGodHammer20261028/CommonSeatsStructuralV7/Meshes/SM_ThunderGodHammer_head_mount_reinforced_block_V7',
    '/Game/Weapons/ThunderGodHammer20261028/CommonSeatsStructuralV7/Meshes/SM_ThunderGodHammer_head_mount_laminated_damper_V7',
    '/Game/Weapons/ThunderGodHammer20261028/LightSeatWindowFixV8/Meshes/SM_ThunderGodHammer_head_mount_ribbed_light_V8'):
    if any(p.get_path_name()==asset_path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving dirty asset')
    for suffix in ('.uasset','.ubulk','.uexp'):
        file=R/'Content'/(asset_path.removeprefix('/Game/')+suffix)
        if file.exists():shutil.copy2(file,backup/file.name)
    mesh=u.load_asset(asset_path)
    settings=mesh.get_editor_property('nanite_settings')
    before=str(settings.fallback_target)
    settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.
    settings.fallback_relative_error=0.
    subsystem.set_nanite_settings(mesh,settings,True)
    if not u.WarhammerModificationAuditCommandlet.repair_seat_tangent_basis(mesh):raise RuntimeError('Basis repair failed: '+asset_path)
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Save failed')
    rows.append(dict(asset=asset_path,before=before,after=str(settings.fallback_target),geometry_reimported=False))
(P/'seat_tangent_receipt.json').write_text(json.dumps(dict(saved=True,assets=rows,backup=str(backup)),indent=2),encoding='utf-8')
print('THOR_SEAT_TANGENTS_SAVED',flush=True)
