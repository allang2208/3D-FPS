"""User-directed ecology detail revision, stock reuse and explicit planting anchors."""
from pathlib import Path
import json,random,math
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Revisions/v3/Config/room.json').read_text('utf8'));n,h,b=cfg['rooms'];base=cfg['ue_base']
fits=json.loads((ROOT/'Sources/StockV4/root-fits.json').read_text('utf8'))
cfg.update(revision='ecology_subject_v4_20261004',layout_revision=4,geometry_revision=5,mesh_base=base+'/RefineV4')
b['size'][2]=9.0
for light in b['lights']:
    if light['position'][2]>6:light['position'][2]-=2.25
    if light['position'][2]>5:light['lumens']*=.85
b['soil_bed']=dict(center=[3,0],radii=[8.8,7.2],edge_z=.022,center_z=.13)
def move_group(room,key,x):
    g=next(g for g in room['container_groups'] if g['id']==key);dx=x-g['position_m'][0];g['position_m'][0]=x
    for c in room['containers']:
        if c['container_id']==room['id']+'.'+key or c['container_id'].startswith(room['id']+'.'+key+'.'):c['position_m'][0]+=dx
    for part in room['parts']:
        if part['mesh'].endswith('RecordsCarcass') and abs(part['position'][0]-(x-dx))<.001:part['position'][0]+=dx
for key,x in [('Filter0',-9.6),('Filter1',-8.2),('Spare',8.8),('Tools0',-15.1),('Tools1',15.1),('Box0',-16.5),('Box1',16.5)]:move_group(h,key,x)
move_group(b,'Tote0',-8.7);move_group(b,'Tote2',-6.3)
for room in cfg['rooms']:
    room['wall_column_keepout_m']=[dict(center=[x,y,room['size'][2]/2],extent=[.325,.35,room['size'][2]/2],clearance=.12) for x in range(int(-room['size'][0]/2)+2,int(room['size'][0]/2),6) for y in (-room['size'][1]/2+.4,room['size'][1]/2-.4)]
    for p in room['parts']:
        if 'RecordsCarcass' in p['mesh']:p['assembly']='records'
plantbase='/Game/PN_tropicalGroundPlants/Meshes/'
rng=random.Random(1042604)
def plant(mesh,p,height,yaw,**extra):
    fit=fits[mesh]
    return dict(mesh=mesh,position=p,height_m=height,yaw=yaw,root_anchor_blender_m=fit['root_blender_m'],source_height_m=fit['height_m'],bury_m=.008,**extra)
n['plants']=[];h['plants']=[];b['plants']=[]
for bench_i,(x,y,angle) in enumerate(n['bench_positions']):
    co,si=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    for tray in range(3):
        for j,k in ((0,0),(0,2),(1,1),(2,0),(2,2),(3,1)):
            dx=-.94+tray*.94-.27+k*.27;dy=-.43+j*.28
            p=[x+dx*co-dy*si,y+dx*si+dy*co,1.024]
            mesh=plantbase+f'tropicalPlant_{1 if y<0 else 3:02d}_{rng.randint(1,3):02d}'
            n['plants'].append(plant(mesh,p,rng.uniform(.20,.40),rng.uniform(-180,180),pot_anchor=p[:],pot_radius_m=.103,bench=bench_i,tray=tray,row=j,column=k))
for cx in (-7,7):
    for cy in (-3.8,3.8):
        for ix in range(8):
            for iy in range(3):
                p=[cx+(ix-3.5)*.70,cy+(iy-1)*.42,.072]
                mesh=plantbase+f'tropicalPlant_{rng.choice((2,3)):02d}_{rng.randint(1,3):02d}'
                h['plants'].append(plant(mesh,p,rng.uniform(.36,.72),rng.uniform(-180,180),pot_anchor=p[:],pot_radius_m=.089,raft=[cx,cy],row=iy,column=ix))
# Root positions and the complete rotated crown bounds must fit inside the soil footprint.
def fits_bed(mesh,height,yaw,x,y):
    f=fits[mesh];scale=height/f['height_m'];co,si=math.cos(math.radians(yaw)),math.sin(math.radians(yaw));root=f['root_blender_m']
    for px in (f['min_m'][0],f['max_m'][0]):
        for py in (f['min_m'][1],f['max_m'][1]):
            dx=(px-root[0])*scale;dy=(py-root[1])*scale
            if ((x+dx*co-dy*si-3)/8.35)**2+((y+dx*si+dy*co)/6.75)**2>1:return False
    return True
attempt=0
while len(b['plants'])<86 and attempt<10000:
    attempt+=1;x=rng.uniform(-5,11);y=rng.uniform(-6.4,6.4)
    if (x-3)**2+y*y<1.35**2:continue
    if any((x-p['position'][0])**2+(y-p['position'][1])**2<.52**2 for p in b['plants']):continue
    mesh=plantbase+f'tropicalPlant_{rng.choice((1,2,3,4,5)):02d}_{rng.randint(1,4):02d}'
    # The fifth species' first variant has low outer fronds; use its shared stem pivot.
    if mesh.endswith('05_01'):continue
    height=rng.uniform(.25,.74) if mesh[-5:-3] in ('04','05') else rng.uniform(.55,1.30)
    yaw=rng.uniform(-180,180)
    if fits_bed(mesh,height,yaw,x,y):b['plants'].append(plant(mesh,[x,y,.08],height,yaw,soil_surface=True))
tree='/Game/RuralAustralia/StaticMeshes/Vegetation/Tree_M_03/SM_Tree_M_03'
b['hero_tree']=plant(tree,[3,0,.13],7.15,24,collision=True)
cfg['revision_notes']=['existing detailed double socket extracted and flush mounted','all nursery plants keyed to actual rotated pot coordinates; basal anchors compensated','wall containers moved to column-free bays','segmented coarse-pipe collision; thin floor hoses non-blocking','Rural Australia scanned tree; 17.6 x 14.4 m continuous soil bed with bounded foliage','biosphere ceiling lowered from 11.7 m to 9 m; lights and hanging services follow','scanned soil base colour, normal and real height; shallow parallax and uneven soil geometry']
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
im=Image.open(ROOT/'Sources/StockV4/T_LC_GroundSoilExcavated_00A_Height.png')
arr=np.asarray(im.resize((256,256),Image.Resampling.BILINEAR),dtype=np.float32);arr=arr[:,:,0] if arr.ndim==3 else arr
arr/=65535 if arr.max()>255 else 255
np.save(ROOT/'Sources/StockV4/soil-height.npy',arr)
print('ECOLOGY_V4_LAYOUT_AUTHORED',len(n['plants']),len(h['plants']),len(b['plants']))
