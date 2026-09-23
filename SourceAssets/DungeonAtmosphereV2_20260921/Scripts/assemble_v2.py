"""Install the V2 authored corridor slice; preserve V1 and the hub map contract.

This script authors and saves a map. It does not start PIE or render previews.
Coordinate data from Blender uses metres/cm with Y mirrored by the FBX importer.
"""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
BACKUP=None # The rejected V1 snapshot is archived outside Content in project trash.
PREFIX='DGN_AV2';FOLDER='DungeonAtmosphereV2'
E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
source=json.loads((ROOT/'Authored/structure-manifest.json').read_text(encoding='utf-8'))
structure=json.loads((ROOT/'Receipts/structure-import.json').read_text(encoding='utf-8'))
generated=json.loads((ROOT/'Receipts/generated-import.json').read_text(encoding='utf-8'))
props=json.loads((ROOT/'assets.json').read_text(encoding='utf-8'))['props']
receipt_file=ROOT/'Receipts/scene-build.json'
previous=json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
counts={'structure_meshes':0,'generated_instances':0,'event_props':0,'lights':0,'damp_decals':0}
receipt={'stage':'preparing','target':TARGET,'backup':BACKUP,'tests_run':False,'runtime_random_layout':False}
placements=[];loaded={}

def write_receipt():receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def rot(yaw=0,pitch=0,roll=0):return u.Rotator(roll=roll,pitch=pitch,yaw=yaw)
def location(cm):return u.Vector(cm[0],-cm[1],cm[2])
def own(actor,label,group):
    actor.set_actor_label(PREFIX+'_'+label);actor.set_folder_path(FOLDER+'/'+group)
    actor.set_editor_property('tags',[u.Name(PREFIX),u.Name('DungeonRegion_'+group)])
    return actor
def load(path):
    if path not in loaded:
        loaded[path]=u.load_asset(path)
        if not loaded[path]:raise RuntimeError('Required V2 source asset missing: '+path)
    return loaded[path]
def static(path,cm,label,group,yaw=0,scale=(1,1,1),collision=True,bottom=False):
    mesh=load(path);pos=location(cm);r=rot(yaw)
    if bottom:
        b=mesh.get_bounds();offset=u.Vector(b.origin.x*scale[0],b.origin.y*scale[1],(b.origin.z-b.box_extent.z)*scale[2])
        pos-=u.MathLibrary.quat_rotate_vector(r.quaternion(),offset)
    actor=own(AA.spawn_actor_from_class(u.StaticMeshActor,pos,r),label,group)
    c=actor.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
    actor.set_actor_scale3d(u.Vector(*scale));c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    if not collision:c.set_editor_property('cast_shadow',False)
    placements.append({'label':label,'mesh':path,'location_ue_cm':list(pos.to_tuple()),'yaw':yaw,'scale':scale,'collision':collision})
    return actor
def prop(asset_id,cm,label,group,yaw=0,scale=(1,1,1),collision=True):
    static(generated[asset_id]['path'],cm,label,group,yaw,scale,collision,bottom=True)
    counts['generated_instances']+=1

# These are mutation preconditions, before touching any map or existing actor.
for p in props:
    if p['id'] not in generated:raise RuntimeError('Wait for required generated asset: '+p['id'])
    load(generated[p['id']]['path'])
for entry in source['objects']:
    value=structure['meshes'][entry['name']]
    load(value['path'] if isinstance(value,dict) else value)
damp=load('/Game/Dungeons/AtmosphereV2/Materials/M_LocalDampStreak')
if UE.get_game_world():raise RuntimeError('Gameplay is active. V2 assets are staged; map install deferred.')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
external=('/Game/__ExternalActors__/GameMaps/L_Dungeon_Prototype/','/Game/__ExternalObjects__/GameMaps/L_Dungeon_Prototype/')
foreign=[p for p in dirty if p!=TARGET and not p.startswith(external)]
if foreign:raise RuntimeError('Unsaved map preserved: '+', '.join(foreign))
target_dirty=[p for p in dirty if p==TARGET or p.startswith(external)]
if target_dirty and previous.get('stage')!='assembling':
    raise RuntimeError('Existing unsaved dungeon edits preserved. Map install deferred.')
current=UE.get_editor_world();receipt['previous_world']=current.get_path_name() if current else None
# Editor duplication also handles the level's external actor packages.
if BACKUP and not E.does_asset_exist(BACKUP):
    backup=E.duplicate_asset(TARGET,BACKUP)
    if not backup or not E.save_loaded_asset(backup,False):raise RuntimeError('Could not preserve V1 map')
if not current or current.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Could not load target dungeon')
receipt['stage']='assembling';write_receipt()
for actor in list(AA.get_all_level_actors()):
    folder=str(actor.get_folder_path()).strip('/')
    if any(folder==f or folder.startswith(f+'/') for f in ('DungeonPrototype','DungeonIndustrialV1',FOLDER)):
        AA.destroy_actor(actor)

for entry in source['objects']:
    name=entry['name'];value=structure['meshes'][name];path=value['path'] if isinstance(value,dict) else value
    detail=name.removeprefix('SM_V2_')
    group=('RuinNiche' if any(w in detail for w in ('Ruin','Breach','Ancient')) else
           'ServiceBays' if any(w in detail for w in ('Workshop','Machine','Recess')) else
           'Terminus' if any(w in detail for w in ('Dogleg','End','ServiceDoor')) else 'Corridor')
    static(path,[0,0,0],detail,group,collision=not any(w in detail for w in ('WetPatches','HangingCables','LightFixtures','Breach_Rebar')))
    counts['structure_meshes']+=1

# Shared with the editable Blender assembly; clear lanes and jambs are authored.
for entry in json.loads((ROOT/'layout.json').read_text())['props']:
    prop(entry['id'],entry['cm'],entry['label'],entry['group'],entry['yaw'],entry['scale'],entry.get('collision',True))
# Generated event-statue candidate retired by the user on 2026-09-22.

# Lighting follows real fixtures; ranges keep distinct pools and dark transitions.
intensities={'Entry':2900,'Workshop':2400,'Corridor':3600,'MachineBay':3100,'Recess':1450,'Breach':3100,'Ruin':3400,'Turn':3000,'Exit':2300}
radii={'Entry':540,'Workshop':490,'Corridor':580,'MachineBay':450,'Recess':320,'Breach':540,'Ruin':580,'Turn':570,'Exit':440}
for lamp in source['lights']:
    name=lamp['id'];actor=own(AA.spawn_actor_from_class(u.PointLight,location(lamp['location_cm'])),'Light_'+name,'Lighting')
    c=actor.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(intensities[name])
    c.set_light_color(u.LinearColor(1,.59,.29,1) if lamp['warm'] else u.LinearColor(.71,.83,1,1))
    c.set_attenuation_radius(radii[name]);c.set_editor_property('source_radius',7);c.set_editor_property('source_length',65)
    c.set_cast_shadows(True);counts['lights']+=1

# Local leaks follow joints and equipment mounting, with varied dimensions.
for index,(cm,yaw,size) in enumerate([
    ([286,14,159],90,[22,57,150]),([1150,14,136],90,[22,43,123]),
    ([1342,385,141],-90,[23,51,141]),([1541,369,170],-90,[20,68,166]),
    ([644,-405,146],90,[23,113,141]),([1118,784,153],-90,[23,99,143]),
    ([1517,-204,126],90,[22,91,123]),([2583,548,169],0,[22,66,165]),
    ([1795,1133,190],-90,[23,136,175])]):
    actor=own(AA.spawn_actor_from_class(u.DecalActor,location(cm),rot(yaw)),'Damp_'+str(index),'SurfaceHistory')
    c=actor.get_component_by_class(u.DecalComponent);c.set_decal_material(damp);c.set_editor_property('decal_size',u.Vector(*size))
    c.set_editor_property('sort_order',1);counts['damp_decals']+=1

own(AA.spawn_actor_from_class(u.PlayerStart,location(source['player_start_cm']),rot()),'PlayerStart','Corridor')
world=UE.get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
pp=own(AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector()),'Exposure','Lighting');pp.set_editor_property('unbound',True)
settings=pp.get_editor_property('settings')
for key,value in [('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',0.0),
    ('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',2.5),
    ('override_auto_exposure_bias',True),('auto_exposure_bias',0.0),
    ('override_bloom_intensity',True),('bloom_intensity',.16),
    ('override_vignette_intensity',True),('vignette_intensity',.12)]:settings.set_editor_property(key,value)
pp.set_editor_property('settings',settings)
if not ED.save_current_level():raise RuntimeError('V2 map save failed; live authored edits preserved')
receipt.update(stage='map_saved',counts=counts,regions=source['regions'],player_start_ue_cm=list(location(source['player_start_cm']).to_tuple()),
    notes='Corrective authored art slice. Existing hub/return portal map contract retained. No runtime topology randomizer or event interaction added.')
write_receipt();(ROOT/'Receipts/placement-manifest.json').write_text(json.dumps(placements,indent=2),encoding='utf-8')
print('DUNGEON_ATMOSPHERE_V2_SAVED '+json.dumps(receipt))
