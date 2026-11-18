"""Scoped chimney-only publication, independent of native shutter reflection."""
import json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ChimneyR7'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve PIE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve dirty map')
backup=OUT/'Before';backup.mkdir(exist_ok=True)
disk=ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
world=u.EditorLoadingAndSavingUtils.load_map(level)
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
mesh=u.load_asset('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR7/Meshes/SM_SmithLoft_Chimney_R7')
if not mesh:raise RuntimeError('New chimney package missing')
changed=0
for actor in actors.get_all_level_actors():
    if actor.get_actor_label()!='Village_Blacksmith_Common':continue
    for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
        if comp.static_mesh and comp.static_mesh.get_name().startswith('SM_SmithLoft_Chimney'):
            actor.modify();comp.modify();comp.set_static_mesh(mesh);changed+=1
if changed!=1:raise RuntimeError('Expected one owned chimney, got '+str(changed))
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Save chimney map')
(OUT/'saved.json').write_text(json.dumps({'map_saved':True,'changed_components':changed,'windows_unchanged':True,'runtime_checked':False},indent=2))
u.log('SMITH_CHIMNEY_R7_SAVED')
