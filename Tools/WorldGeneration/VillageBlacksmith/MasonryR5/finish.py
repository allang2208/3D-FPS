"""Import R5 masonry and save only the smith revision and its cleared forecourt."""
import json,os,runpy,shutil
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/MasonryR5'
LOFT=HERE.parent/'LoftR3'
E=u.EditorAssetLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
previous=editor.get_editor_world() if editor else None
previous_path=previous.get_path_name().split('.')[0] if previous else None
map_path=ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
backup=OUT/'Before/L_AbandonedVillage.umap';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(map_path,backup)
manifest=json.loads((OUT/'model-manifest.json').read_text(encoding='utf-8'))
for row in manifest['assets']:
 path='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/LoftR3/Meshes/'+row['name']
 if E.does_asset_exist(path):continue
 os.environ['SMITH_LOFT_SOURCE']=str(OUT);os.environ['SMITH_LOFT_IMPORT_ROLE']=row['role']
 try:runpy.run_path(str(LOFT/'import_assets.py'),run_name='__main__')
 finally:os.environ.pop('SMITH_LOFT_SOURCE',None);os.environ.pop('SMITH_LOFT_IMPORT_ROLE',None)
published=runpy.run_path(str(LOFT/'publish_revision.py'),run_name='__main__')
level='/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
world=u.EditorLoadingAndSavingUtils.load_map(level)
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
removed_rows=json.loads((OUT/'removed-front-walls.json').read_text(encoding='utf-8'))
removed=[]
for actor in actors.get_all_level_actors():
 for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
  mesh=comp.static_mesh
  if not mesh or not mesh.get_name().startswith('SM_H_StoneWall_'):continue
  candidates=[r['instance'] for r in removed_rows if r['instance']['mesh'].split('.')[0]==mesh.get_path_name().split('.')[0]]
  for index in range(comp.get_instance_count()-1,-1,-1):
   t=comp.get_instance_transform(index,True);p=t.translation
   for row in candidates:
    if sum((v-w)**2 for v,w in zip((p.x,p.y,p.z),row['pos']))<1:
     actor.modify();comp.modify();comp.remove_instance(index)
     removed.append(dict(mesh=mesh.get_path_name(),position=[p.x,p.y,p.z]));break
if not u.EditorLoadingAndSavingUtils.save_map(world,level):raise RuntimeError('Save cleared smith forecourt')
report=dict(level=level,map_saved=True,assets=[a['name'] for a in manifest['assets']],
    shaft_width_cm=146,previous_shaft_width_cm=92,chimney_position_cm=[200,500,0],
    stone_source='/Game/UnrealNormandy/StaticMeshes/SM_H_OldWall_00A',
    removed_front_wall_instances=removed,default_state='ruined',
    torch_class='/Script/FPSGAME.BronzeTorch',torch_count=3,torches_require_repair=True,
    interior_torches_always_lit=True,entry_torch_uses_weather_clock=True,
    gameplay_tested=False,engine_preview_rendered=False)
(OUT/'saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if previous_path and previous_path!=level and E.does_asset_exist(previous_path):u.EditorLoadingAndSavingUtils.load_map(previous_path)
u.log('SMITH_MASONRY_R5_SAVED meshes=3 removed_front_walls='+str(len(removed)))
