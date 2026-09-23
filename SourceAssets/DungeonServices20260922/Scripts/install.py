"""One mutex-owned import/install batch for the requested dungeon revision."""
import json,runpy
from pathlib import Path
from datetime import datetime
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/AtmosphereV2/Services';MAP='/Game/GameMaps/L_Dungeon_Prototype'
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem);LE=u.get_editor_subsystem(u.LevelEditorSubsystem)
if not UE or Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Requires FPSGAME editor')
if UE.get_game_world():raise RuntimeError('Preserve active gameplay')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+str([p.get_path_name() for p in dirty]))
if UE.get_editor_world().get_path_name().split('.')[0]!=MAP:raise RuntimeError('Dungeon must be loaded for this scoped authoring batch')
MAN=json.loads((ROOT/'Authored/geometry-manifest.json').read_text());CFG=MAN['config']
actors={a.get_actor_label():a for a in AA.get_all_level_actors()};targets=[]
for entry in MAN['objects']:
    actor=actors.get(entry['actor']);c=actor.get_component_by_class(u.StaticMeshComponent) if actor else None
    new=BASE+'/Meshes/'+entry['name']
    if not c or not c.static_mesh:raise RuntimeError('Missing '+entry['actor'])
    if c.static_mesh.get_path_name() not in (entry['previous_mesh'],new+'.'+entry['name']):raise RuntimeError('Preserve independent mesh edit '+entry['actor'])
    if any(c.get_editor_property('override_materials')):raise RuntimeError('Preserve material override '+entry['actor'])
    targets.append((entry,actor,c))
lights=[]
for label,xyz in CFG['light_positions_cm'].items():
    actor=actors.get(label)
    if not actor or not actor.get_component_by_class(u.RectLightComponent):raise RuntimeError('Required light missing '+label)
    lights.append((actor,xyz))
fixture_actor=actors.get('DGN_AV2_LightFixtures')
fixture=fixture_actor.get_component_by_class(u.StaticMeshComponent) if fixture_actor else None
fixture_base='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopTools/Meshes/'
fixture_name='SM_WSTools_OtherFixturesWithoutRuin'
if not fixture or fixture.static_mesh.get_name() not in ('SM_WSTools_OtherFixtures',fixture_name):raise RuntimeError('Preserve independently revised fixture bank')
fixture_replacement=u.load_asset(fixture_base+fixture_name)
ruin_actor=actors.get('DGN_AV2_Light_Ruin')
if not fixture_replacement or not ruin_actor:raise RuntimeError('Required existing ruin retirement inputs missing')
if not globals().get('SERVICES_SKIP_IMPORT',False):
    if not globals().get('SERVICES_SKIP_MATERIALS',False):runpy.run_path(str(ROOT/'Scripts/import_materials.py'),run_name='__main__')
    runpy.run_path(str(ROOT/'Scripts/import_meshes.py'),run_name='__main__',init_globals={'SERVICES_MESH_NAMES':globals().get('SERVICES_MESH_NAMES')})
receipt=dict(stage='scene_changed',map=MAP,actors=[],lights=[],gameplay_tests=False)
for entry,actor,c in targets:
    actor.modify();c.modify();old=c.static_mesh.get_path_name();mesh=u.load_asset(BASE+'/Meshes/'+entry['name'])
    if not mesh:raise RuntimeError('Missing authored mesh '+entry['name'])
    c.set_static_mesh(mesh)
    receipt['actors'].append(dict(label=entry['actor'],previous_mesh=old,mesh=mesh.get_path_name()))
for actor,xyz in lights:
    old=list(actor.get_actor_location().to_tuple());actor.modify();actor.set_actor_location(u.Vector(*xyz),False,False)
    receipt['lights'].append(dict(label=actor.get_actor_label(),before=old,after=xyz))
fixture_actor.modify();fixture.modify();fixture.set_static_mesh(fixture_replacement)
ruin_actor.modify();ruin=ruin_actor.get_component_by_class(u.LightComponent);ruin.modify();ruin.set_visibility(False);ruin.set_intensity(0)
receipt['retired_legacy_ruin_fixture']=fixture_replacement.get_path_name()
receipt['retired_legacy_ruin_light']='DGN_AV2_Light_Ruin'
(ROOT/'Receipts').mkdir(exist_ok=True)
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if not LE.save_current_level():raise RuntimeError('Map save failed; retain scene changes')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat())
(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('DUNGEON_SERVICES_INSTALLED '+json.dumps(receipt))
