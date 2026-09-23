"""Retire the rejected prop instances and install authored maintenance panels."""
import unreal as u,json,runpy
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];MAP='/Game/GameMaps/L_Dungeon_Prototype'
plan=json.loads((ROOT/'Config/retirement.json').read_text());config=json.loads((ROOT/'Config/cabinet.json').read_text())
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem);LE=u.get_editor_subsystem(u.LevelEditorSubsystem)
if not UE or Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Requires FPSGAME editor')
if UE.get_game_world():raise RuntimeError('Preserve active gameplay')
if UE.get_editor_world().get_path_name().split('.')[0]!=MAP:raise RuntimeError('Preserve current map; dungeon is required')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
if any(any(p.startswith(r+'/') for r in plan['ue_roots']) for p in dirty):raise RuntimeError('Rejected assets have unsaved changes; retain them')
if not globals().get('MAINTENANCE_SKIP_IMPORT',False):runpy.run_path(str(ROOT/'Scripts/import_cabinet.py'),run_name='__main__',init_globals={'MAINTENANCE_RESUME_ASSETS':globals().get('MAINTENANCE_RESUME_ASSETS',[])})
mesh=u.load_asset('/Game/Dungeons/AtmosphereV2/Maintenance/Meshes/SM_MaintenanceCabinet')
if not mesh:raise RuntimeError('Authored cabinet asset missing')
receipt=dict(stage='scene_changed',removed=[],installed=[],tests_run=False,rendered=False)
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
for a in list(actors.values()):
    matches=[c.static_mesh.get_path_name() for c in a.get_components_by_class(u.StaticMeshComponent)
        if c.static_mesh and any(c.static_mesh.get_path_name().startswith(r+'/') for r in plan['ue_roots'])]
    if not matches:continue
    if not a.get_actor_label().startswith('DGN_'):raise RuntimeError('Generated prop used by another scene actor; preserve '+a.get_actor_label())
    receipt['removed'].append(dict(actor=a.get_actor_label(),meshes=matches,location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple())))
    if not AA.destroy_actor(a):raise RuntimeError('Could not retire '+a.get_actor_label())
for entry in config['placements']:
    a=actors.get(entry['label'])
    if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector())
    a.modify();a.set_actor_label(entry['label']);a.set_folder_path('DungeonAtmosphereV2/AuthoredMaintenance')
    a.set_actor_location_and_rotation(u.Vector(*entry['location_cm']),u.Rotator(roll=0,pitch=0,yaw=entry['yaw']),False,True)
    a.set_actor_scale3d(u.Vector(1,1,1));c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_static_mesh(mesh)
    c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll');c.set_editor_property('cast_shadow',True)
    receipt['installed'].append(dict(actor=entry['label'],mesh=mesh.get_path_name(),location=entry['location_cm'],yaw=entry['yaw']))
(ROOT/'Receipts').mkdir(exist_ok=True)
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if not LE.save_current_level():raise RuntimeError('Map save failed; retain scene state')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat())
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('MAINTENANCE_INSTALLED '+json.dumps(receipt))
