"""Finish collision on the three substantial additions inside existing rack bays."""
from pathlib import Path
import json,runpy
import unreal as u
ROOT=Path(__file__).resolve().parent
scope=runpy.run_path(str(ROOT/'install.py'))
TARGET=scope['TARGET'];TAG=scope['TAG'];PLAN=scope['PLAN']
if Path(u.Paths.project_dir()).resolve()!=scope['PROJECT'].resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
if any('/gamemaps/design/l_freighttransit_theme_subject/' in p.get_name().lower() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved subject actors')
previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
w=u.EditorLoadingAndSavingUtils.load_map(TARGET)
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor) if TAG in [str(t) for t in a.tags]}
receipt=ROOT/'Receipts/install.json';report=json.loads(receipt.read_text('utf8'));rows=[]
for r in PLAN['parts']:
    if r['group']!='Rack' or r['collision']!='BlockAll':continue
    mesh=scope['blocking_mesh'](r['mesh']);a=actors['WarehouseEntrance_'+r['id']]
    a.modify();c=a.static_mesh_component;c.modify();c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll')
    rows.append(r['id']);report['mesh_assets'][r['mesh']+'|BlockAll']=mesh.get_path_name()
scope['save_world'](w)
report['rack_collision_completed']=rows;receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if previous and not previous.startswith('/Temp/') and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
print('ENTRANCE_RACK_COLLISION_SAVED '+str(len(rows)),flush=True)
