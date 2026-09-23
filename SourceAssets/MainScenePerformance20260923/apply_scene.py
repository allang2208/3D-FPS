"""Persist the corrected floor LOD and local Nanite instance groups; no PIE."""
from pathlib import Path
import importlib.util, json, shutil
import unreal as u
ROOT=Path(__file__).parent;PROJECT=ROOT.parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=UE.get_editor_world()
if UE.get_game_world() or not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/DayNight_Lighting':
    raise RuntimeError('Open DayNight_Lighting in editor mode; preserve current session')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map changes; do not merge them into this batch')
source=PROJECT/'Content/GameMaps/DayNight_Lighting.umap'
backup=PROJECT/'trash/main-scene-performance-20260923/SourceAssets/MainScenePerformance20260923/Before/Content/GameMaps/DayNight_Lighting.umap'
if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
api=u.get_editor_subsystem(u.EditorActorSubsystem)
floors=[]
for actor in api.get_all_level_actors():
    tags={str(t) for t in actor.tags}
    if 'ColdSteel.MainPlaza.Generated' not in tags or 'ColdSteel.MainPlaza.Paving' not in tags or not isinstance(actor,u.StaticMeshActor):continue
    c=actor.static_mesh_component
    if not c.static_mesh or c.static_mesh.get_num_lods()<2:raise RuntimeError('Paving needs existing LOD1 before forcing it: '+actor.get_actor_label())
    floors.append(actor)
if not floors:raise RuntimeError('No generated paving actors found; preserve the map')
with u.ScopedEditorTransaction('Main scene performance: correct floor LOD and local instances'):
    for actor in floors:
        actor.modify();c=actor.static_mesh_component;c.modify();c.set_forced_lod_model(2);c.set_cast_shadow(False)
    spec=importlib.util.spec_from_file_location('main_scene_plaza_instances',ROOT/'plaza_instances.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    clusters=module.apply()
    if not u.EditorLoadingAndSavingUtils.save_map(world,'/Game/GameMaps/DayNight_Lighting'):raise RuntimeError('Save failed; preserve editor state')
report={'map':world.get_path_name(),'paving_components':len(floors),'forced_lod_model':2,'target_lod_index':1,
        'instancing':clusters,'saved':True,'runtime_tested':False}
dest=ROOT/'Receipts/scene.json';dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':True,'paving':len(floors),'clusters':len(clusters['clusters']),'components_removed':clusters['components_removed']},ensure_ascii=False))
