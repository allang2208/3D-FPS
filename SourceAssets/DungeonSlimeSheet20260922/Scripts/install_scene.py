"""Replace only generated tile layers, hanging fluid and its puddle impact material."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ROOMS=ROOT.parent/'DungeonRoomShells20260922'
CFG=json.loads((ROOMS/'Config/rooms.json').read_text(encoding='utf-8'))
IM=json.loads((ROOT/'Receipts/meshes.json').read_text());FLUID=json.loads((ROOT/'Authored/fluids.json').read_text())
AA=u.get_editor_subsystem(u.EditorActorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():raise RuntimeError('End current play before dungeon integration')
target=CFG['target_map']
if UE.get_editor_world().get_path_name().split('.')[0]!=target:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve the current unsaved map before opening the dungeon')
    if not ED.load_level(target):raise RuntimeError('Cannot open dungeon')
actors={}
for a in AA.get_all_level_actors():actors.setdefault(a.get_actor_label(),[]).append(a)
changed=[];snapshot=[]
def own(label):
    found=actors.get(label,[])
    if len(found)!=1:raise RuntimeError('Expected one existing actor '+label)
    a=found[0];c=a.get_component_by_class(u.StaticMeshComponent)
    snapshot.append(dict(label=label,mesh=c.static_mesh.get_path_name(),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
    a.modify();c.modify();changed.append(label)
    return a,c
for name,path in IM['meshes'].items():
    if not name.startswith('SM_RS_'):continue
    a,c=own('DGN_RS_'+name.removeprefix('SM_RS_'))
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing authored tile mesh '+path)
    c.set_static_mesh(mesh);c.set_editor_property('override_materials',[])
dr=next(r for r in CFG['rooms'] if r['id']=='Drainage')
for item in FLUID['objects']:
    a,c=own('DGN_RS_Drainage_'+item['name'].removeprefix('SM_'))
    mesh=u.load_asset(IM['meshes'][item['name']])
    if not mesh:raise RuntimeError('Missing authored fluid '+item['name'])
    c.set_static_mesh(mesh);c.set_editor_property('override_materials',[])
    c.set_collision_profile_name('NoCollision');c.set_cast_shadow(False);c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('evaluate_world_position_offset',True);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
    p=item['local_m'];o=dr['origin_m'];a.set_actor_location(u.Vector(100*(o[0]+p[0]),-100*(o[1]+p[1]),100*(o[2]+p[2])),False,True)
item=next(i for i in dr['pipe_slime']['objects'] if i['name']=='SM_PipePusPuddle')
a,c=own('DGN_RS_Drainage_PipePusPuddle')
material=u.load_asset(item['material_override'])
if not material:raise RuntimeError('Missing puddle impact material')
c.set_material(0,material)
before=ROOT/'Receipts/scene-before.json'
if not before.exists():before.write_text(json.dumps(snapshot,indent=2))
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save changed dungeon actor packages')
if not ED.save_current_level():raise RuntimeError('Cannot save dungeon map')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=target,updated=changed,saved_packages=len(owned),tests_run=False),indent=2))
print('CONVERGING_SLIME_MAP_SAVED',len(changed),'actors')
