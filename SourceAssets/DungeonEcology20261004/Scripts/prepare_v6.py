"""V6: dense central garden, several existing trees and reused office equipment."""
from pathlib import Path
import json,random,math
from ecology_garden_layout import bed_margin,bed_height,PATHS,DRY_RECTS
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Revisions/v5/Config/room.json').read_text('utf8'))
fits=json.loads((ROOT/'Sources/StockV4/root-fits.json').read_text('utf8'))
cfg.update(revision='ecology_subject_v6_20261004',layout_revision=6,geometry_revision=7,
    mesh_base=cfg['ue_base']+'/RefineV6',soil_material_base=cfg['ue_base']+'/RefineV5')
n,h,b=cfg['rooms']
n['runtime_actors'][0]['position_m'][1]=3.0
b['soil_bed']['dry_rects']=DRY_RECTS
b['trees']=[]
for name,x,y,height,yaw in [('Tree_M_01',-9,-7,5.9,35),('Tree_M_02',10,-7.3,6.1,-40),
    ('Tree_M_04',-4,3.1,5.3,75),('Tree_M_01',14,3.8,4.2,155),('Tree_L_01',2,-8.5,6.8,-65)]:
    path='/Game/RuralAustralia/StaticMeshes/Vegetation/'+name+'/SM_'+name;f=fits[path]
    b['trees'].append(dict(mesh=path,position=[x,y,bed_height(x,y)],height_m=height,yaw=yaw,
        root_anchor_blender_m=f['root_blender_m'],source_height_m=f['height_m'],bury_m=.025))
tree_positions=[b['hero_tree']]+b['trees']
b['plants']=[];rng=random.Random(1042606)
for attempt in range(40000):
    if len(b['plants'])>=850:break
    x,y=rng.uniform(-21.4,21.4),rng.uniform(-12.4,11.7)
    if bed_margin(x,y)<.30:continue
    if any(math.hypot(x-t['position'][0],y-t['position'][1])<.85 for t in tree_positions):continue
    if any(math.hypot(x-p['position'][0],y-p['position'][1])<.40 for p in b['plants']):continue
    species=rng.choice((1,2,3,4,4,4,5,5));variant=rng.randint(1,3)
    path=f'/Game/PN_tropicalGroundPlants/Meshes/tropicalPlant_{species:02d}_{variant:02d}'
    if path not in fits or path.endswith('05_01'):continue
    f=fits[path];height=rng.uniform(.22,.58) if species>=4 else rng.uniform(.48,1.18)
    if bed_margin(x,y)>2 and species<=3:height*=1.15
    yaw=rng.uniform(-180,180);scale=height/f['height_m'];root=f['root_blender_m']
    co,si=math.cos(math.radians(yaw)),math.sin(math.radians(yaw));corners=[]
    for px in (f['min_m'][0],f['max_m'][0]):
        for py in (f['min_m'][1],f['max_m'][1]):
            dx=(px-root[0])*scale;dy=(py-root[1])*scale;corners.append((x+dx*co-dy*si,y+dx*si+dy*co))
    if any(bed_margin(px,py)<.08 for px,py in corners):continue
    b['plants'].append(dict(mesh=path,position=[x,y,bed_height(x,y)],height_m=height,yaw=yaw,
        root_anchor_blender_m=root,source_height_m=f['height_m'],bury_m=.01,soil_surface=True))
# The existing detailed station monitor/keyboard/mouse assembly is extracted unchanged.
b['parts']=[p for p in b['parts'] if not p['mesh'].endswith('/SM_Staff_Chair')]
for x in (-22.1,-20.3):
    b['parts'].append(dict(mesh=cfg['mesh_base']+'/Meshes/SM_Eco_StationDesktopReuse',position=[x,10.96,.83],yaw=0,collision=False))
b['parts'].append(dict(mesh='/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_Chair',position=[-22.1,9.83,0],yaw=180,collision=True,role='monitoring_office_chair'))
cfg['revision_notes']=['Full-depth window reveal frame and fitted sill collision',
    'Remove northwest scattered beds by monitoring office and left stairs',
    'Dense bounded understorey and five additional existing trees across four forms',
    'Reuse station desktop equipment geometry/materials and existing office chair']
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('ECOLOGY_V6_LAYOUT',len(b['plants']),len(tree_positions))
