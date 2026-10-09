"""Local window reveal correction and a wall-based monitoring-office layout."""
from pathlib import Path
import json,runpy
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Revisions/v6/Config/room.json').read_text('utf8'))
cfg.update(revision='ecology_subject_v7_20261005',layout_revision=7,geometry_revision=8,
    mesh_base=cfg['ue_base']+'/RefineV7',tree_material_base=cfg['ue_base']+'/RefineV6')
b=cfg['rooms'][2]
# Table fits the north-wall bay between the columns at x=-22 and x=-16.
# Its rear edge is 12 cm clear of the structural wall's inner face (y=16.36).
b['monitoring_desk']=dict(center=[-19,15.74,.79],size=[4.8,1.0,.08],
    wall_gap_m=.12,front_access_depth_m=1.5)
for p in b['parts']:
    if p['mesh'].endswith('SM_Eco_StationDesktopReuse') or p.get('role')=='monitoring_office_chair':
        p['position'][0]+=2.;p['position'][1]+=4.94
        p['assembly']='monitoring_desk'
# Separate storage functions along the west wall; preserve all container IDs,
# drawer heights, hinge settings and existing meshes.
for key,y in [('PPE0',8.8),('PPE1',10.0),('Records0',13.2),('Records1',14.4)]:
    g=next(g for g in b['container_groups'] if g['id']==key);old=g['position_m'][:]
    g['position_m'][:2]=[-23.5,y];g['yaw_blender']=-90
    mount=dict(axis=0,plane=-23.78,side=-1,gap_m=.055)
    for c in b['containers']:
        if c['container_id']=='EcoBiosphere.'+key or c['container_id'].startswith('EcoBiosphere.'+key+'.'):
            c['position_m'][:2]=[-23.5,y];c['yaw_blender']=-90;c['wall_mount']=dict(mount)
    if key.startswith('Records'):
        p=next(p for p in b['parts'] if p['mesh'].endswith('RecordsCarcass') and abs(p['position'][0]-old[0])<.01)
        p['position'][:2]=[-23.5,y];p['yaw']=-90;p['wall_mount']=dict(mount)
b['furniture_keepout_m']=[
    dict(center=[-19,15.74,.415],extent=[2.4,.5,.415],role='monitoring_table'),
    dict(center=[-20.1,14.55,.5],extent=[.55,.65,.5],role='chair_pullback'),
    dict(center=[-17.8,7.9,1.25],extent=[1.10,.75,1.25],role='office_door_access')]
cfg['revision_notes']=['Continuous window frame rings with no overlapping corner faces; metal reveals 2 cm proud of masonry jamb planes',
    'Monitoring table and existing desktop equipment moved together to north-wall bay',
    'PPE and records cabinets relocated separately along west wall, preserving interactive identities']
chest_receipt=ROOT/'Receipts/upper-platform-chest-20261005.json'
if chest_receipt.exists() and json.loads(chest_receipt.read_text('utf8')).get('stage')=='maps_saved':
    cfg=runpy.run_path(str(ROOT/'Scripts/ecology_treasure.py'))['apply'](cfg)
current=json.loads((ROOT/'Config/room.json').read_text('utf8'))
if current.get('phase')=='production':
    for key in ('phase','random_pool_registered','accepted_by_user','production_map','production_revision','production_modules','subject_status','theme_candidates','branches_per_run'):
        if key in current:cfg[key]=current[key]
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('ECOLOGY_V7_LAYOUT_SAVED')
