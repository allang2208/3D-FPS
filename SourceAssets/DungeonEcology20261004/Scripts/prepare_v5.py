"""Ecology V5: usable glazing, supported hydroponics and an indoor garden."""
from pathlib import Path
import json, math, random
from ecology_garden_layout import bed_margin, bed_height, PATHS, DRY_RECTS

ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Revisions/v4/Config/room.json').read_text('utf8'))
n,h,b=cfg['rooms'];base=cfg['ue_base'];newbase=base+'/RefineV5'
cfg.update(revision='ecology_subject_v5_20261004',layout_revision=5,geometry_revision=6,mesh_base=newbase)
fits=json.loads((ROOT/'Sources/StockV4/root-fits.json').read_text('utf8'))

def window(room,key,center,width,height):
    return dict(type='glass_window',id=key,position_m=center,yaw_ue=90,
        pane=newbase+'/Meshes/SM_Eco_'+key+'PaneV5',
        fracture=newbase+'/Meshes/SM_Eco_'+key+'FractureV5',dimensions_cm=[width*100,height*100,.65],
        fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',
        impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',
        sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0')

n['runtime_actors']=[window(n,'NurseryWindow',[-10,2.84,2.09],5.59,2.29)]
b['runtime_actors']=[]
for i in range(3):
    spec=window(b,'MonitorWide',[-23.82+(i+.5)*1.75,6.84,2.13],1.68,2.23)
    spec['id']='MonitorWide'+str(i);b['runtime_actors'].append(spec)
b['runtime_actors'].append(window(b,'MonitorNarrow',[-16.605,6.84,2.13],.78,2.23))
b['runtime_actors'].append(dict(type='solid_door',id='MonitorDoor',position_m=[-17.8,6.84,.008],
    yaw_ue=90,leaf='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/SM_SW_PersonnelLeaf',
    positive_hinge=True,open_seconds=.55,auto_close_seconds=0))
h['runtime_actors']=[]
b['soil_bed']=dict(type='natural_garden',outer_extent_m=[43.2,25],paths=PATHS,dry_rects=DRY_RECTS,
    main_path_clear_width_m=2.5,secondary_path_clear_width_m=2.2)
b['hero_tree']['height_m']=8.05
b['hero_tree']['position']=[3,0,bed_height(3,0)]
b['plants']=[];rng=random.Random(1042605)
plantbase='/Game/PN_tropicalGroundPlants/Meshes/'
for attempt in range(18000):
    if len(b['plants'])>=310:break
    x=rng.uniform(-21.4,21.4);y=rng.uniform(-12.4,11.7)
    if bed_margin(x,y)<.45 or math.hypot(x-3,y)<1.15:continue
    if any(math.hypot(x-p['position'][0],y-p['position'][1])<.64 for p in b['plants']):continue
    species=rng.choice((1,2,3,4,4,5));variant=rng.randint(1,3)
    mesh=plantbase+f'tropicalPlant_{species:02d}_{variant:02d}'
    if mesh not in fits or mesh.endswith('05_01'):continue
    height=rng.uniform(.26,.65) if species>=4 else rng.uniform(.55,1.35)
    # Low planting beside paths; taller grouped specimens in the inner beds.
    if bed_margin(x,y)>2.0 and species<=3:height*=1.15
    yaw=rng.uniform(-180,180);f=fits[mesh];scale=height/f['height_m'];root=f['root_blender_m']
    co,si=math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
    corners=[]
    for px in (f['min_m'][0],f['max_m'][0]):
        for py in (f['min_m'][1],f['max_m'][1]):
            dx=(px-root[0])*scale;dy=(py-root[1])*scale
            corners.append((x+dx*co-dy*si,y+dx*si+dy*co))
    if any(bed_margin(px,py)<.10 for px,py in corners):continue
    b['plants'].append(dict(mesh=mesh,position=[x,y,bed_height(x,y)],height_m=height,yaw=yaw,
        root_anchor_blender_m=root,source_height_m=f['height_m'],bury_m=.01,soil_surface=True))

staff='/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_'
for x in (-22,-20):b['parts'].append(dict(mesh=staff+'Chair',position=[x,9.7,0],yaw=180,collision=True))
cfg['revision_notes']=['soil height sampler matches Masks texture compression; bounded parallax retained',
 'replace static window blockers with visible breakable panes; independent nursery sill and clear landing',
 'low hydro main at 96 cm with continuous convex collision and shared guardrail traversal',
 'hydro beds supported down to basin slab by frames, footplates and cross braces',
 'monitor suite: framed glazing and station personnel door with E and sprint push',
 '43.2 x 25 m natural garden envelope; clipped soil, 2.5 m main route, 2.2 m loop, clear stair aprons',
 'stock tree raised from 7.15 to 8.05 m with original uniform proportions']
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('ECOLOGY_V5_LAYOUT_AUTHORED',len(b['plants']),flush=True)
