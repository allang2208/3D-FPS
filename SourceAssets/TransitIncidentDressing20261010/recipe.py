"""Bounded incident dressing for FacilityTransit; all positions are room-local UE centimetres."""
from pathlib import Path
import copy,json,random,math
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/TransitIncidentDressing20261010';MODULE='FacilityTransit';REVISION='transit_incident_20261010'
SUBJECTS=('/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject')
BLOOD='/Game/Dungeons/IsolationWard20260929/BloodScan/M_WardBlood_Quixel'
CHAIR='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/SM_Staff_Chair'
EXTINGUISHER='/Game/Dungeons/ArtPass20260922/Meshes/SM_Prop_Extinguisher'
CLIPBOARD='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/SM_SW_DispatchPaper'

def manifest():return json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
def added(row):return row.get('incident_revision')==REVISION

def placements():
    rows=[];rng=random.Random(20261010)
    def part(id,kind,xyz,yaw=0,**fields):
        mesh=kind if kind.startswith('/Game/') else BASE+'/Meshes/SM_Incident_'+kind
        rows.append(dict(id='Incident_'+id,mesh=mesh,position=xyz,yaw=yaw,scale=[1,1,1],materials=[],fluid=False,
            collision=False,cast_shadow=True,instanced=True,incident_revision=REVISION,**fields))
    # Lower west gallery: cleaning abandoned between wall bench and circulation row.
    part('CleaningBucket','Bucket',[-2110,-810,0],27)
    part('CleaningMop','Mop',[-1985,-907,0],-59)
    part('CleaningWarning','WarningSign',[-2140,-1047,0],-22)
    # Administrative spill at the upper duty desk; another folder was carried downstairs.
    part('DutyFolder','Folder',[-2175,998,420],-41)
    part('DutyBasket','WasteBasket',[-2310,1100,420],138)
    part('LowerFolder','Folder',[-2108,835,0],23)
    part('LowerClipboard',CLIPBOARD,[-2055,760,0],-53)
    # Fallen chair and extinguisher use their actual saved source geometry/materials.
    # A quarter-turn maps a bound axis directly onto Z; support heights come from
    # each actual saved mesh's bounds, with no diagonal bounding-box approximation.
    part('PPEChair',CHAIR,[-210,-1380,0],31,roll=90,pitch=0,settle_floor_cm=0)
    part('PPEExtinguisher',EXTINGUISHER,[-66,-1460,0],-36,roll=90,pitch=0,settle_floor_cm=0)
    part('ServiceClipboard',CLIPBOARD,[155,1567,0],121)
    part('ServiceFolder','Folder',[12,1460,0],-143)
    # Distinct clusters: dense near the origin of each spill and thinner at its edge.
    specs=[('Duty',(-2160,1100,420),(102,185),17),
           ('Lower',(-2080,750,0),(102,165),13),
           ('PPE',(-122,-1330,0),(157,75),13),
           ('Service',(20,1480,0),(198,90),12)]
    for cluster,(cx,cy,z),(rx,ry),count in specs:
        used=[]
        for i in range(count):
            for attempt in range(80):
                angle=rng.random()*math.tau;radius=math.sqrt(rng.random())
                x=cx+rx*math.cos(angle)*radius;y=cy+ry*math.sin(angle)*radius
                if all((x-px)**2+(y-py)**2>23**2 for px,py in used):break
            used.append((x,y))
            part(cluster+'Paper'+str(i),'Paper'+str(i%4),[round(x,2),round(y,2),z],rng.uniform(-180,180),cast_shadow_override=False)
    # A few sheets show the direction of hurried movement without creating a carpet.
    for i,(x,y) in enumerate(((-1895,677),(-1790,620),(-1650,560),(-1455,518),(-1265,485),
            (-232,-1080),(-132,-939),(-84,-769),(202,1380),(272,1225))):
        part('TrailPaper'+str(i),'Paper'+str((i+1)%4),[x,y,0],rng.uniform(-170,170),cast_shadow_override=False)
    for row in rows:
        if row.pop('cast_shadow_override',None) is False:row['cast_shadow']=False
    return rows

def blood_marks():
    # Keep the scanned image's square aspect. Smaller offset stains suggest movement;
    # never stretch one scan into an obvious long rectangle.
    spots=[(-274,-1370,76,18),(-201,-1282,64,103),(-188,-1185,39,-37),
        (-162,-1064,31,146),(-120,-943,24,76),(-76,-802,20,-51),
        (-2046,794,56,-73),(-1946,718,35,122),(-1810,654,23,11),
        (78,1517,49,201),(164,1409,29,68)]
    return [dict(id='Incident_Blood'+str(i),type='decal',position=[x,y,.4],pitch=-90,yaw=yaw,roll=0,
        material=BLOOD,decal_size=[1.2,size/2,size/2],sort_order=6,fade_screen_size=.002,
        incident_revision=REVISION) for i,(x,y,size,yaw) in enumerate(spots)]

def settled_placements():
    rows=placements();path=ROOT/'placements.json'
    if path.exists():
        saved={row['id']:row for row in json.loads(path.read_text('utf8'))}
        for row in rows:
            if 'settle_floor_cm' in row:
                if row['id'] not in saved:raise RuntimeError('Missing source support transform '+row['id'])
                row['position']=saved[row['id']]['position'];row.pop('settle_floor_cm')
    elif any('settle_floor_cm' in row for row in rows):raise RuntimeError('Run installation to derive reused prop support heights')
    return rows

def apply_module(module):
    if module['id']!=MODULE:return
    module['parts']=[p for p in module['parts'] if not added(p)]+settled_placements()
    module['runtime_actors']=[p for p in module.get('runtime_actors',[]) if not added(p)]+blood_marks()
    assets={p['mesh'] for p in settled_placements()}|{BLOOD}|{v for m in manifest() for v in m['materials'].values()}
    module['runtime_assets']=sorted(set(module.get('runtime_assets',[]))|assets)
    module['incident_revision']=REVISION

def installed():
    path=ROOT/'Receipts/install.json'
    return path.exists() and json.loads(path.read_text('utf8')).get('stage')=='maps_saved'

def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    out=copy.deepcopy(catalog);apply_module(next(m for m in out['modules'] if m['id']==MODULE))
    out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out);return out

def apply_subject(world):
    import unreal as u
    if world.get_path_name().split('.')[0] not in SUBJECTS:return {}
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};changed=[]
    for row in settled_placements()+blood_marks():
        label='FacilityTransit_'+row['id'];actor=actors.get(label)
        if actor and REVISION not in [str(t) for t in actor.tags]:raise RuntimeError('Preserve unowned '+label)
        loc=u.Vector(row['position'][0]+5900,row['position'][1],row['position'][2]);rot=u.Rotator(pitch=row.get('pitch',0),yaw=row['yaw'],roll=row.get('roll',0))
        is_decal=row.get('type')=='decal'
        if not actor:actor=aa.spawn_actor_from_class(u.DecalActor if is_decal else u.StaticMeshActor,loc,rot);actor.set_actor_label(label)
        actor.modify();sc=actor.get_component_by_class(u.DecalComponent if is_decal else u.StaticMeshComponent);sc.modify();sc.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_location_and_rotation(loc,rot,False,True)
        if is_decal:
            sc.set_decal_material(u.load_asset(row['material']));sc.set_editor_property('decal_size',u.Vector(*row['decal_size']))
            sc.set_sort_order(row['sort_order']);sc.set_fade_screen_size(row['fade_screen_size'])
        else:
            sc.set_static_mesh(u.load_asset(row['mesh']));sc.set_cast_shadow(row['cast_shadow']);sc.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            sc.set_editor_property('generate_overlap_events',False);sc.set_editor_property('receives_decals',False)
        sc.set_mobility(u.ComponentMobility.STATIC);actor.set_folder_path('FacilityTransit/IncidentDressing')
        actor.set_editor_property('tags',['FacilityTransit.Subject',REVISION]);changed.append(label)
    return dict(parts=sum('mesh' in r for r in settled_placements()),blood_decals=len(blood_marks()),actors=changed)
