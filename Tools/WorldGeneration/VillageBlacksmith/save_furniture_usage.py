"""Persist instanced-mesh shader support for the furniture materials used by village HISMs."""
import json,shutil
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parents[3]
out=root/'SourceAssets/HillsVillageBlacksmith20261117'
L,E=u.MaterialEditingLibrary,u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Active play session retained; defer material writes until play has ended.')
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
paths=[
    '/Game/Props/CastingStation20260926/RealismV5/M_OakDry',
    '/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron',
    '/Game/UnrealNormandy/MaterialInstances/MI_StoneWall_Pieces_00B_Gray',
    '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Materials/M_WornLinen',
    '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Materials/M_BlacksmithSign',
    '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Materials/M_ClosedPlaque']
saved=[];seen=set()
for path in paths:
    mat=u.load_asset(path)
    while isinstance(mat,u.MaterialInstanceConstant):mat=mat.get_editor_property('parent')
    package=mat.get_path_name().split('.')[0]
    if package in seen:continue
    seen.add(package)
    if mat.get_editor_property('used_with_instanced_static_meshes'):continue
    if package in dirty:raise RuntimeError('Preserve existing unsaved material edits: '+package)
    file=Path(package.replace('/Game/','Content/')+'.uasset');backup=out/'Before'/file
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/file,backup)
    L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Save material usage '+package)
    saved.append(package)
(out/'furniture-usage-saved.json').write_text(json.dumps(dict(saved=saved),indent=2),encoding='utf-8')
