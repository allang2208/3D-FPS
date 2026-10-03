"""Promote the accepted V7 descriptors to complete production room modules."""
import copy,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];STAFF=ROOT.parent;PROJECT=STAFF.parents[1]
def read(p):return json.loads(p.read_text('utf-8-sig'))
cfg=read(STAFF/'Config/room.json');draft=read(STAFF/'Config/modules-draft.json')
catalog=read(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json')
pool=next(m for m in catalog['modules'] if m['id']=='Distribution')['spawn']
modules=[]
for original in draft['modules']:
    m=copy.deepcopy(original);rid=m['id']
    m.update(phase='production',staff_living=True,random_pool_registered=True,revision=cfg['revision'],
        encounter_role='themed_combat',selection=dict(chance_per_run=1,max_per_run=1,route='StaffThemeOnly'))
    m.pop('layout_actor_class',None);m.pop('recreation_chair_layout_actor_class',None)
    for p in m['parts']:
        p.setdefault('scale',[1,1,1]);p.setdefault('fluid',False);p['affects_navigation']=p['collision']
    for p in m.pop('variable_static_furniture',[]):
        m['parts'].append(dict(p,scale=[1,1,1],collision=True,affects_navigation=True,fluid=False,materials=[]))
    # Include the actual 14cm outer wall thickness; end ports stay at the author planes.
    for c in m['cells']:
        if c['max'][0]-c['min'][0]>400 and c['max'][1]-c['min'][1]>300:
            for axis in (0,1):c['min'][axis]-=14;c['max'][axis]+=14
        else:c['min'][1]-=14;c['max'][1]+=14
    m['min']=[min(c['min'][i] for c in m['cells']) for i in range(3)]
    m['max']=[max(c['max'][i] for c in m['cells']) for i in range(3)]
    m['walk_mask']=[]
    for area in m['author_walk_rects_m']:
        x0,y0,x1,y1=area[:4];z=area[4] if len(area)>4 else 0
        m['walk_mask'].append(dict(min=[x0*100,-y1*100,z*100-5],max=[x1*100,-y0*100,z*100+280]))
    a,b=(p['position'] for p in m['ports'])
    m['walk_polyline']=[a,b]
    m['spawn']=copy.deepcopy(pool)
    m['spawn'].update(source='DungeonStaffLiving20261002',theme='staff_living',count=[3,5],
        anchor_roles=['encounter'],sealed_encounter=True)
    m['side_sockets']=[];m['scene_recipes']=[]
    for l in m['lights']:
        l.update(intensity=l.pop('lumens'),radius=l.pop('radius_cm'),color=l.pop('tint'),
            type='point',indirect_lighting_intensity=l.pop('indirect',.65))
        l['role']=l['role'].lower();l['optimized_radius_cm']=l['radius']
    lo,hi=m['min'],m['max']
    pp=dict(cfg['postprocess'],type='post_process',position=[(lo[i]+hi[i])/2 for i in range(3)],
        extent=[(hi[i]-lo[i])/2 for i in range(3)],yaw=0,priority=2,blend_radius=150)
    m['runtime_actors']=[pp]
    modules.append(m)
expansion=PROJECT/'SourceAssets/SceneLootExpansion20261003';saved=expansion/'Receipts/install.json'
if saved.exists() and read(saved).get('stage')=='maps_saved':
    modules=runpy.run_path(str(expansion/'Scripts/extend_catalog.py'))['extend']({'modules':modules})['modules']
data=dict(sequence=draft['sequence'],modules=modules,container_outline=draft['container_outline'],
    accepted_revision=cfg['revision'],source='Config/modules-draft.json',rewards_deferred=True)
(ROOT/'Config/modules.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
extend=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend']
(ROOT/'Config/catalog-pending.json').write_text(json.dumps(extend(catalog),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_PRODUCTION_MODULES_AUTHORED',len(modules),sum(len(m['scene_containers']) for m in modules))
