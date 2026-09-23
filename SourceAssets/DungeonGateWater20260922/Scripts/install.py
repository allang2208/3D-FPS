"""Replace only the two existing gate/puddle meshes; preserve actor placement."""
import unreal as u,json,runpy
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/AtmosphereV2/GateWater';MAP='/Game/GameMaps/L_Dungeon_Prototype'
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem);LE=u.get_editor_subsystem(u.LevelEditorSubsystem)
if not UE or Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('FPSGAME editor required')
if UE.get_game_world():raise RuntimeError('Preserve active gameplay')
if UE.get_editor_world().get_path_name().split('.')[0]!=MAP:raise RuntimeError('Preserve current level; dungeon required')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
MAN=json.loads((ROOT/'Authored/manifest.json').read_text());actors={a.get_actor_label():a for a in AA.get_all_level_actors()};targets=[]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(('/Game/__ExternalActors__/GameMaps/L_Dungeon_Prototype/','/Game/__ExternalObjects__/GameMaps/L_Dungeon_Prototype/')) for p in dirty):raise RuntimeError('Preserve unsaved dungeon actors')
for entry in MAN['meshes']:
    actor=actors.get(entry['actor']);c=actor.get_component_by_class(u.StaticMeshComponent) if actor else None
    if not c or not c.static_mesh:raise RuntimeError('Missing target '+entry['actor'])
    path=c.static_mesh.get_path_name().split('.')[0]
    if path not in (entry['old_mesh'],BASE+'/Meshes/'+entry['name']):raise RuntimeError('Preserve revised mesh '+entry['actor'])
    if any(c.get_editor_property('override_materials')):raise RuntimeError('Preserve material override '+entry['actor'])
    targets.append((entry,actor,c))
if not globals().get('GATE_WATER_SKIP_IMPORT',False):runpy.run_path(str(ROOT/'Scripts/import_assets.py'),run_name='__main__')
receipt=dict(stage='scene_changed',actors=[],tests_run=False,rendered=False)
for entry,a,c in targets:
    mesh=u.load_asset(BASE+'/Meshes/'+entry['name'])
    if not mesh:raise RuntimeError('Authored asset missing '+entry['name'])
    previous=c.static_mesh.get_path_name();a.modify();c.modify();c.set_static_mesh(mesh)
    if not entry['collision']:
        c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False)
        c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False)
    receipt['actors'].append(dict(actor=a.get_actor_label(),previous_mesh=previous,mesh=mesh.get_path_name(),location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple())))
(ROOT/'Receipts').mkdir(exist_ok=True);(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if not LE.save_current_level():raise RuntimeError('Map save failed; preserve current state')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat())
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('DUNGEON_GATE_WATER_INSTALLED '+json.dumps(receipt))
