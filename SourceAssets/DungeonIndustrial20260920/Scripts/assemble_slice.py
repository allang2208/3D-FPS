"""Install the approved art slice using cell boundaries and room-scoped HISM.

Run through mcp_call_codex.ps1 -PythonScript. Saves only the dungeon map and
this task's new materials. An on-disk and an editor asset backup preserve V0.
Does not run PIE, navigation tests, captures or a lighting benchmark.
"""
import json
import math
import random
import shutil
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonIndustrial20260920')
CFG = json.loads((ROOT/'layout.json').read_text(encoding='utf-8'))
KIT = json.loads((ROOT/'Receipts/kit-build.json').read_text(encoding='utf-8'))
INPUT = json.loads((ROOT/'Receipts/authoring-inputs.json').read_text(encoding='utf-8'))
TARGET = CFG['target_map']
BACKUP = '/Game/Dungeons/IndustrialV1/Archive/L_Dungeon_PreIndustrial20260920'
PREFIX = 'DGN_IV1'
EAL = u.EditorAssetLibrary
ED = u.get_editor_subsystem(u.LevelEditorSubsystem)
AA = u.get_editor_subsystem(u.EditorActorSubsystem)
UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
SUB = u.get_engine_subsystem(u.SubobjectDataSubsystem)
BFL = u.SubobjectDataBlueprintFunctionLibrary
groups = {}
counts = {'instances':0,'hism_components':0,'static_props':0,'lights':0}
placements = []
receipt = {'stage':'preparing','target':TARGET,'backup':BACKUP,'tests_run':False}


def record():
    (ROOT/'Receipts/scene-build.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')


def rot(v=(0,0,0)):
    return u.Rotator(roll=v[0],pitch=v[1],yaw=v[2])


def transform(loc, rotation=(0,0,0), scale=(1,1,1)):
    return u.Transform(location=u.Vector(*loc),rotation=rot(rotation),scale=u.Vector(*scale))


def name_actor(a, name, room):
    a.set_actor_label(PREFIX+'_'+name)
    a.set_folder_path('DungeonIndustrialV1/'+room)
    a.set_editor_property('tags',[u.Name(PREFIX),u.Name('DungeonRoom_'+room)])
    return a


def place(kind, loc, room, rotation=(0,0,0), scale=(1,1,1), collision=True):
    path = KIT['meshes'][kind]
    key = (room,path,collision)
    groups.setdefault(key,[]).append(transform(loc,rotation,scale))
    placements.append({'room':room,'mesh':path,'location':loc,'rotation':rotation,'scale':scale,'collision':collision})


def imported(meshpath, center, room, label, rotation=(0,0,0), scale=(1,1,1), bottom=False, collision=True):
    m = u.load_asset(meshpath)
    if not m:
        raise RuntimeError('Missing source mesh '+meshpath)
    b=m.get_bounds()
    pivot=u.Vector(b.origin.x*scale[0],b.origin.y*scale[1],
                   (b.origin.z-b.box_extent.z if bottom else b.origin.z)*scale[2])
    r=rot(rotation)
    loc=u.Vector(*center)-u.MathLibrary.quat_rotate_vector(r.quaternion(),pivot)
    a=name_actor(AA.spawn_actor_from_class(u.StaticMeshActor,loc,r),label,room)
    c=a.static_mesh_component
    c.set_static_mesh(m)
    c.set_mobility(u.ComponentMobility.STATIC)
    a.set_actor_scale3d(u.Vector(*scale))
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    counts['static_props']+=1
    return a


def imported_id(key,center,room,label,**kw):
    return imported(INPUT['assets'][key]['path'],center,room,label,**kw)


def lamp(loc, room, warm=False, intensity=5000, radius=650, shadow=False):
    place('CeilingLamp_Warm' if warm else 'CeilingLamp_Cool',loc,room,collision=False)
    a=name_actor(AA.spawn_actor_from_class(u.PointLight,u.Vector(loc[0],loc[1],loc[2]-35)),
                 'Light_'+str(counts['lights']),room)
    c=a.get_component_by_class(u.PointLightComponent)
    c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
    c.set_intensity(intensity)
    c.set_light_color(u.LinearColor(1,.62,.29,1) if warm else u.LinearColor(.73,.84,1,1))
    c.set_attenuation_radius(radius)
    c.set_editor_property('source_radius',12)
    c.set_editor_property('source_length',95)
    c.set_cast_shadows(shadow)
    counts['lights']+=1


def sign(text,loc,room,yaw=180,size=24):
    a=name_actor(AA.spawn_actor_from_class(u.TextRenderActor,u.Vector(*loc),rot((0,0,yaw))),
                 'Wayfinding_'+str(len(placements)),room)
    c=a.get_component_by_class(u.TextRenderComponent)
    c.set_text(text)
    c.set_world_size(size)
    c.set_text_render_color(u.Color(196,172,116,255))
    c.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    c.set_vertical_alignment(u.VerticalTextAligment.EVRTA_TEXT_CENTER)


# These reads are required before changing the active world, to preserve unsaved work.
if UE.get_game_world():
    raise RuntimeError('Editor is in gameplay; assets are ready but map install deferred.')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
target_external=('/Game/__ExternalActors__/GameMaps/L_Dungeon_Prototype/',
                 '/Game/__ExternalObjects__/GameMaps/L_Dungeon_Prototype/')
foreign=[p for p in dirty if p != TARGET and not p.startswith(target_external)]
if foreign:
    raise RuntimeError('Unsaved map preserved; cannot switch map: '+', '.join(foreign))
current=UE.get_editor_world()
receipt['previous_world']=current.get_path_name() if current else None
if TARGET in dirty:
    owned=[a for a in AA.get_all_level_actors() if PREFIX in [str(t) for t in a.tags]]
    if not owned:
        raise RuntimeError('Dungeon has existing unsaved edits; leaving them intact.')

# Backup first, including original binary on disk. Never overwrite either backup.
disk=Path('D:/FPS3D/FPSGAME/Content/GameMaps/L_Dungeon_Prototype.umap')
raw=ROOT/'Archive/L_Dungeon_Prototype.umap'
raw.parent.mkdir(exist_ok=True)
if not raw.exists():
    shutil.copy2(disk,raw)
if not EAL.does_asset_exist(BACKUP):
    backup=EAL.duplicate_asset(TARGET,BACKUP)
    if not backup or not EAL.save_loaded_asset(backup,False):
        raise RuntimeError('Could not preserve original dungeon asset.')
if current.get_path_name().split('.')[0] != TARGET and not ED.load_level(TARGET):
    raise RuntimeError('Could not load dungeon target.')
world=UE.get_editor_world()
for a in list(AA.get_all_level_actors()):
    folder=str(a.get_folder_path()).strip('/')
    if folder == 'DungeonPrototype' or folder.startswith('DungeonIndustrialV1'):
        AA.destroy_actor(a)

receipt['stage']='assembling'
record()

# The same shape data can be consumed by a future runtime layout assembler.
# Shared edges have a single owner; both rooms use the same door opening.
edges={}
doors={(d['axis'],d['i'],d['j'],0) for d in CFG['connections']}
for r in CFG['rooms']:
    x0,y0=r['origin_cell']; w,d=r['size_cells']; levels=r['height_cells']; room=r['id']
    for i in range(x0,x0+w):
        for j in range(y0,y0+d):
            place('Floor_400',((i+.5)*400,(j+.5)*400,0),room)
            place('Ceiling_400',((i+.5)*400,(j+.5)*400,levels*400-20),room)
    for z in range(levels):
        for i in range(x0,x0+w):
            for j in (y0,y0+d):
                edges.setdefault(('x',i,j,z),room)
        for j in range(y0,y0+d):
            for i in (x0,x0+w):
                edges.setdefault(('y',i,j,z),room)
for (axis,i,j,z),room in sorted(edges.items()):
    kind='DoorWall_200x280' if (axis,i,j,z) in doors else ('Wall_Concrete_400' if z else 'Wall_Tiled_400')
    loc=((i+.5)*400,j*400,z*400) if axis=='x' else (i*400,(j+.5)*400,z*400)
    place(kind,loc,room,rotation=(0,0,0 if axis=='x' else 90))

# Reinforced returns/pier trims finish module joints without shrinking door openings.
for room,points,height in [
    ('maintenance',[(0,0),(0,800),(800,0),(800,800),(1600,800)],1),
    ('pump_hall',[(1600,-400),(1600,1600),(4000,-400),(4000,1600)],2),
    ('ruin_event',[(4000,400),(4000,2000),(5600,400),(5600,2000)],1)]:
    for x,y in points:
        for z in range(height):
            place('CornerPier',(x,y,400*z),room)

# Maintenance corridor: service lane and machinery stay along the perimeter.
for x in (0,400,800,1200):
    for y,z in ((65,300),(65,350),(738,305)):
        place('Pipe_Flanged_400',(x,y,z),'maintenance')
    place('DrainGrate_400',(x,160,1),'maintenance',collision=False)
for x in (450,1120):
    place('ValveWheel',(x,65,300),'maintenance',rotation=(0,0,180),collision=False)
for x in (650,1320):
    place('ElectricalCabinet',(x,758,0),'maintenance')
for x in (300,850,1380):
    lamp((x,415,361),'maintenance',warm=(x==1380),intensity=3600,radius=650,shadow=(x==850))
place('WetPatch',(1000,160,.1),'maintenance',rotation=(0,0,20),collision=False)
sign('PUMP HALL  /  02',(1578,200,312),'maintenance',size=21)
sign('SERVICE  /  01',(20,390,240),'maintenance',yaw=0,size=23)

# Pump hall: two deliberate islands, circulation loop and a 4 m high usable catwalk.
for n,(x,y) in enumerate(((2500,0),(3250,750))):
    place('PumpIsland',(x,y,0),'pump_hall',rotation=(0,0,0 if n==0 else 180))
    place('WetPatch',(x+210,y+30,.12),'pump_hall',rotation=(0,0,37),collision=False)
for x in range(1600,4000,400):
    for y,z in ((-340,270),(-340,325),(1540,665)):
        place('Pipe_Flanged_400',(x,y,z),'pump_hall')
    place('DrainGrate_400',(x,-250,1),'pump_hall',collision=False)
for x in (2200,3400):
    for y in (-250,1180):
        # Pack columns are authored along +X: rotate to vertical and center at 390.
        column_scale=780/(INPUT['assets']['SM_Column_Medium_5M']['extent'][0]*2)
        imported_id('SM_Column_Medium_5M',(x,y,390),'pump_hall','SteelColumn',rotation=(0,90,0),scale=(column_scale,1,1))
for x in (1800,2200,2600,3000,3400,3800):
    imported_id('SM_Catwalk_Floor_4x2M',(x,1460,387.74),'pump_hall','Catwalk')
    # Upper tread ends at x=1900, y=1340: leave the landing edge open there.
    for xx in (x-100,x+100):
        if xx >= 2100 or xx == 1700:
            imported_id('SM_Catwalk_Floor_Railing_2M',(xx,1360,442.2),'pump_hall','CatwalkRail')
place('StairFlight_Rise200',(1900,500,0),'pump_hall',rotation=(0,0,90))
place('StairLanding',(1900,850,200),'pump_hall',rotation=(0,0,90))
place('StairFlight_Rise200',(1900,990,200),'pump_hall',rotation=(0,0,90))
place('Floor_400',(1900,1340,400),'pump_hall',scale=(.5,.15,1))
# The source floor upper bound is +4.52 cm; chosen center yields a walk surface at 400.
for center in ((2200,200,728),(3200,300,728),(2600,1050,728),(3600,1100,728)):
    lamp(center,'pump_hall',intensity=14000,radius=1150,shadow=center[0] in (2200,3600))
lamp((3860,1000,360),'pump_hall',warm=True,intensity=4200,radius=600)
lamp((2900,1470,351),'pump_hall',intensity=3500,radius=650)
for x in (2900,3070):
    place('ElectricalCabinet',(x,-358,0),'pump_hall',rotation=(0,0,180))
sign('RESTRICTED  /  03',(3976,1000,315),'pump_hall',size=22)
sign('P-02',(2500,-337,210),'pump_hall',yaw=90,size=35)

# Event chamber: industry surrounds one concentrated ancient breach.
for x in range(4000,5600,400):
    place('Pipe_Flanged_400',(x,445,322),'ruin_event')
for x in (4200,4550):
    place('ElectricalCabinet',(x,1956,0),'ruin_event')
place('BreachBacking',(5200,1800,0),'ruin_event')
place('AncientArch',(5200,1700,0),'ruin_event',scale=(.9,1,.85))
place('EventPlinth',(5200,1510,0),'ruin_event')
for x in (4950,5450):
    place('BreachRubble',(x,1670,0),'ruin_event',rotation=(0,0,x%71))
    imported_id('SM_Column_Small_5M',(x,1720,182),'ruin_event','BreachShoring',rotation=(0,90,0),scale=(.72,1.4,1.4))
for x in (5147,5245):
    place('AnomalySeam',(x,1766,240),'ruin_event',rotation=(0,-11 if x<5200 else 16,0),collision=False)
imported_id('SM_Beam_4M',(5200,1720,361),'ruin_event','BreachLintel',rotation=(0,0,90),scale=(1,1.3,1))
place('WetPatch',(4420,1250,.1),'ruin_event',scale=(.6,.6,1),collision=False)
lamp((4320,1000,361),'ruin_event',intensity=3300,radius=650)
lamp((4900,1390,345),'ruin_event',warm=True,intensity=3900,radius=650,shadow=True)
lamp((5410,750,361),'ruin_event',intensity=2800,radius=650)
sign('KEEP CLEAR',(4024,1000,312),'ruin_event',yaw=0,size=20)
prop_file=ROOT/'Receipts/event-prop.json'
if prop_file.exists():
    prop=json.loads(prop_file.read_text(encoding='utf-8'))
    scale=228/(prop['extent'][2]*2)
    imported(prop['mesh'],(5200,1490,103),'ruin_event','Goddess_Candidate',scale=(scale,scale,scale),bottom=True,rotation=(0,0,180))
    receipt['event_prop']=prop['mesh']
else:
    receipt['event_prop']='not installed; imported prop is a separate required stage'

# Constrained decor variation: no debris scatters in the start, doorway or stairs.
rng=random.Random(CFG['seed'])
for n,(x,y) in enumerate(((1100,735),(3600,-300),(4450,1900),(5460,1900))):
    place('BreachRubble',(x+rng.uniform(-20,20),y,0),'maintenance' if n==0 else ('pump_hall' if n==1 else 'ruin_event'),
          rotation=(0,0,rng.uniform(0,360)),scale=(.4,.4,.4),collision=False)

# Persist real HISM components through the editor's subobject subsystem.
for path in KIT['materials'].values():
    material=u.load_asset(path)
    material.set_editor_property('used_with_instanced_static_meshes',True)
    u.MaterialEditingLibrary.recompile_material(material)
    if not EAL.save_loaded_asset(material,False):
        raise RuntimeError('Could not save instancing material '+path)
for (room,path,collision),instances in groups.items():
    a=name_actor(AA.spawn_actor_from_class(u.Actor,u.Vector(0,0,0)),path.rsplit('/',1)[1],room)
    handles=SUB.k2_gather_subobject_data_for_instance(a)
    params=u.AddNewSubobjectParams()
    params.set_editor_property('parent_handle',handles[0])
    params.set_editor_property('new_class',u.HierarchicalInstancedStaticMeshComponent)
    handle,reason=SUB.add_new_subobject(params)
    if not BFL.is_handle_valid(handle):
        raise RuntimeError('Could not create room HISM: '+str(reason))
    c=BFL.get_associated_object(BFL.get_data(handle))
    c.set_mobility(u.ComponentMobility.STATIC)
    c.set_static_mesh(u.load_asset(path))
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    c.set_editor_property('cast_shadow',collision)
    for instance in instances:
        c.add_instance(instance,world_space=True)
    counts['instances']+=len(instances)
    counts['hism_components']+=1

start=name_actor(AA.spawn_actor_from_class(u.PlayerStart,u.Vector(*CFG['player_start_cm']),rot()),'PlayerStart','maintenance')
world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
# Indoor-only environment; no sun or sky lights washing out roughness/occlusion.
pp=name_actor(AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector(0,0,0)),'Exposure','Environment')
pp.set_editor_property('unbound',True)
settings=pp.get_editor_property('settings')
for key,value in [('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',0.0),
                  ('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',3.0),
                  ('override_auto_exposure_bias',True),('auto_exposure_bias',0.0),
                  ('override_bloom_intensity',True),('bloom_intensity',.18),
                  ('override_vignette_intensity',True),('vignette_intensity',.15)]:
    settings.set_editor_property(key,value)
pp.set_editor_property('settings',settings)

if not ED.save_current_level():
    raise RuntimeError('Dungeon map save failed; live authored map is preserved.')
receipt.update(stage='map_saved',counts=counts,seed=CFG['seed'],cell_cm=400,rooms=CFG['rooms'],
               runtime_random_layout=False,notes='Art slice only. No encounters, event interaction or runtime streaming added.')
record()
(ROOT/'Receipts/placement-manifest.json').write_text(json.dumps(placements,indent=2),encoding='utf-8')
print('DUNGEON_INDUSTRIAL_SAVED '+json.dumps(receipt))
