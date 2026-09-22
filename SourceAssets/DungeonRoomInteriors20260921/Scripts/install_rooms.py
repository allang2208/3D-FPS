"""Place only the two approved room revisions, retaining previous actor state."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRoomInteriors20260921')
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
AA=u.get_editor_subsystem(u.EditorActorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
manifest=json.loads((ROOT/'Authored/room-manifest.json').read_text())
assets=json.loads((ROOT/'Receipts/asset-import.json').read_text())
path=ROOT/'Receipts/room-install.json'
receipt=json.loads(path.read_text()) if path.exists() else {'stage':'ready','map':TARGET,'tests_run':False,'screenshots_taken':False}
phase=globals().get('ROOM_INSTALL_PHASE','complete')

def write():path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def rot(yaw=0,pitch=0):return u.Rotator(roll=0,pitch=pitch,yaw=yaw)
def pos(cm):return u.Vector(cm[0],-cm[1],cm[2])
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Required room asset missing '+p)
    return a
def static(actor,mesh,collision):
    c=actor.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(mesh)
    c.set_editor_property('override_materials',[]);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    c.set_editor_property('cast_shadow',True)
    return c
def own(label,cls,point=None,r=None):
    a=actors.get(label)
    if not a:
        a=AA.spawn_actor_from_class(cls,point or u.Vector(),r or rot());a.set_actor_label(label)
        a.set_folder_path('DungeonAtmosphereV2/RoomInteriors/'+('Workshop' if '_WS_' in label else 'Ruin'))
        a.set_editor_property('tags',[u.Name('DungeonRoomInteriors20260921')]);actors[label]=a
    return a
def bottom_place(actor,mesh,cm,yaw,scale):
    b=mesh.get_bounds();r=rot(yaw)
    offset=u.Vector(b.origin.x*scale[0],b.origin.y*scale[1],(b.origin.z-b.box_extent.z)*scale[2])
    p=pos(cm)-u.MathLibrary.quat_rotate_vector(r.quaternion(),offset)
    actor.set_actor_location_and_rotation(p,r,False,True);actor.set_actor_scale3d(u.Vector(*scale))

if UE.get_game_world():raise RuntimeError('Gameplay remains active; map preserved')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty and receipt['stage']!='assembling':raise RuntimeError('Unsaved editor map preserved: '+', '.join(dirty))
world=UE.get_editor_world()
receipt.setdefault('previous_editor_map',world.get_path_name() if world else None)
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if dirty:raise RuntimeError('Cannot change a dirty editor map')
    if not ED.load_level(TARGET):raise RuntimeError('Could not load dungeon map for room install')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
required=manifest['hidden_existing']+[p['label'] for p in manifest['prop_moves']]+['DGN_AV2_Goddess_Candidate','DGN_AV2_LightFixtures','DGN_AV2_Light_Workshop','DGN_AV2_Light_Ruin']
for label in required:
    if label not in actors:raise RuntimeError('Room input actor missing: '+label)
meshes={e['name']:load(assets['meshes'][e['name']]) for e in manifest['objects']}
generated={} if phase=='authored' else {p['id']:load(assets['generated'][p['id']]) for p in manifest['new_generated']}
decals={n:load(assets['materials'][n]) for n in ('Oil','Dust','Leak')}

# Preserve the precise live references before the first room mutation.
previous_file=ROOT/'Receipts/previous-room-state.json'
if not previous_file.exists():
    previous={}
    for label in required:
        a=actors[label]
        d={'location':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple()),'hidden':a.get_editor_property('hidden'),'temporarily_hidden':a.is_temporarily_hidden_in_editor()}
        c=a.get_component_by_class(u.StaticMeshComponent)
        if c:d.update(mesh=c.static_mesh.get_path_name() if c.static_mesh else None,collision_profile=str(c.get_collision_profile_name()))
        light=a.get_component_by_class(u.PointLightComponent)
        if light:d.update(intensity=light.intensity,visibility=light.get_editor_property('visible'))
        decal=a.get_component_by_class(u.DecalComponent)
        if decal:d['visibility']=decal.get_editor_property('visible')
        previous[label]=d
    previous_file.write_text(json.dumps(previous,indent=2),encoding='utf-8')
receipt['stage']='assembling';write()

for entry in manifest['objects']:
    mesh=meshes[entry['name']]
    actor=actors[entry['replace_actor']] if entry.get('replace_actor') else own(entry['actor_label'],u.StaticMeshActor)
    if entry.get('replace_actor'):
        actor.get_component_by_class(u.StaticMeshComponent).set_static_mesh(mesh)
    else:static(actor,mesh,entry['collision'])
    actor.set_actor_location_and_rotation(u.Vector(),rot(),False,True);actor.set_actor_scale3d(u.Vector(1,1,1))

for label in manifest['hidden_existing']:
    actor=actors[label];actor.set_actor_hidden_in_game(True);actor.set_is_temporarily_hidden_in_editor(True)
    actor.set_actor_enable_collision(False)
    c=actor.get_component_by_class(u.StaticMeshComponent)
    if c:c.set_visibility(False)
    c=actor.get_component_by_class(u.DecalComponent)
    if c:c.set_visibility(False)
for entry in manifest['prop_moves']:
    a=actors[entry['label']];mesh=a.get_component_by_class(u.StaticMeshComponent).static_mesh
    bottom_place(a,mesh,entry['cm'],entry['yaw'],entry['scale'])
for entry in manifest['new_generated']:
    if phase=='authored':continue
    mesh=generated[entry['id']];a=own(entry['label'],u.StaticMeshActor)
    static(a,mesh,True);bottom_place(a,mesh,entry['cm'],entry['yaw'],entry['scale'])

statue=actors['DGN_AV2_Goddess_Candidate'];c=statue.get_component_by_class(u.StaticMeshComponent)
s=statue.get_actor_scale3d();yaw=statue.get_actor_rotation().yaw
bottom_place(statue,c.static_mesh,manifest['statue_anchor_blender_cm'],yaw,[s.x,s.y,s.z])
actors['DGN_AV2_Light_Ruin'].get_component_by_class(u.PointLightComponent).set_visibility(False)
old_light=actors['DGN_AV2_Light_Workshop'].get_component_by_class(u.PointLightComponent)
old_light.set_intensity(650);old_light.set_light_color(u.LinearColor(1,.82,.66,1))
for e in manifest['lights']:
    a=own(e['label'],u.PointLight,pos(e['cm']));a.set_actor_location(pos(e['cm']),False,True)
    c=a.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(e['intensity']);c.set_attenuation_radius(e['radius'])
    c.set_light_color(u.LinearColor(*e['color'],1));c.set_editor_property('source_radius',4);c.set_cast_shadows(True)
for e in manifest['decals']:
    label='DGN_Room_Decal_'+e['label'];a=own(label,u.DecalActor,pos(e['cm']),rot(e['yaw'],e['pitch']))
    a.set_actor_location_and_rotation(pos(e['cm']),rot(e['yaw'],e['pitch']),False,True)
    c=a.get_component_by_class(u.DecalComponent);c.set_decal_material(decals[e['material']]);c.set_editor_property('decal_size',u.Vector(*e['extent']));c.set_editor_property('sort_order',5)

if not ED.save_current_level():raise RuntimeError('Room scene save failed; live edits preserved')
receipt.update(stage='authored_saved' if phase=='authored' else 'map_saved',authored_meshes=len(manifest['objects']),generated_masters=len(generated),generated_instances=0 if phase=='authored' else len(manifest['new_generated']),
    local_lights=len(manifest['lights']),local_decals=len(manifest['decals']),hidden_previous=manifest['hidden_existing'],
    runtime_random_generator_changed=False,visual_acceptance='pending user',source_blend=str(ROOT/'Authored/DungeonRooms_Authored.blend'))
write();print('DUNGEON_ROOMS_SAVED '+json.dumps(receipt))
