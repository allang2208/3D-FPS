"""Author-time variations; doorway datums and object dimensions are never scaled."""
import copy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('Config','Authored','Receipts','Sources'): (ROOT/name).mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
repairs=read(ROOT.parent/'DungeonRouteRepairs20260922/Config/rooms.json')
vf=read(ROOT.parent/'DungeonVentFreight20260922/Config/rooms.json')
base_d=next(r for r in repairs['rooms'] if r['id']=='Drainage_CombatDoor')
base_v=next(r for r in vf['rooms'] if r['id']=='VentilationLoop')
socket_recipes=read(ROOT.parent/'DungeonRouteRepairs20260922/Config/replacements.json')['sockets']
rooms=[];main=[]
for family,recipes in [('Drainage',[('NearBridge',-.8,-1.45),('FarBridge',.8,1.45)]),
                       ('VentilationLoop',[('WestCore',-.75,1.0),('EastCore',.75,1.8)])]:
    for label,a,b in recipes:
        r=copy.deepcopy(base_d if family=='Drainage' else base_v)
        r.update(id=family+'_'+label,family_id=family,source_id=family,origin_m=[0,0,0])
        r.pop('export_kinds',None)
        r['surface_seed_id']=r['id'];r['surface_variant']=0
        if family=='Drainage':
            old_y=max(p[1] for p in r['footprint'])
            for p in r['footprint']:
                if abs(p[1]-old_y)<.001:p[1]+=a
            for rect in r['floors']+r['ceilings']:
                if abs(rect[3]-old_y)<.001:rect[3]+=a
            r['trench']['bridge_y']=[y+b for y in r['trench']['bridge_y']]
            old_bridge=sum(base_d['trench']['bridge_y'])/2
            for light in r['lights']:
                if abs(light['at'][1]-old_bridge)<.05:light['at'][1]+=b
                elif light['at'][1]>16.3:light['at'][1]+=a/2
            for anchor in r['anchors']:
                if anchor['role']=='loop_bridge':anchor['at'][1]+=b
                elif anchor['at'][1]>16.3:anchor['at'][1]+=a/2
            r['dressing_parameters']={'rear_delta_cm':a*100,'bridge_delta_cm':b*100}
            # Existing pipes and fluids stay in the unchanged main hall/trench.
            r['export_kinds']=['Shell','Tiles','Frames','Floors','Ceilings','Bridge','Fixtures']
        else:
            c=b;r['footprint']=[[c,0],[18-c,0],[18,c],[18,16-c],[18-c,16],[c,16],[0,16-c],[0,c]]
            r['core_offset_x']=a
            r['core']['rect'][0]+=a;r['core']['rect'][2]+=a
            r['openings'][0]['center']=6-c;r['openings'][1]['center']=12-c
            # Keep service pipes within both corner chamfers; their bore stays circular.
            for p in r['pipes']:
                p['points'][0][1]=1.3
                p['points'][1][1]=14.5;p['points'][2][1]=14.5
            for anchor in r['anchors']:
                if anchor['role']=='filter_maintenance':anchor['at'][0]+=a
            for light in r['lights']:light['at'][0]+=a*.25
            r['dressing_parameters']={'core_offset_cm':a*100}
        main.append(copy.deepcopy(r));rooms.append(r)
        # All side-door replacements are generated from the same structural recipe.
        for socket in socket_recipes[family]:
            s=copy.deepcopy(r);s['id']=r['id']+'_Side'+socket['id'];s['export_kinds']=['Shell','Tiles','Frames']
            x,y=socket['position'][0]/100,-socket['position'][1]/100
            for edge,(p,q) in enumerate(zip(s['footprint'],s['footprint'][1:]+s['footprint'][:1])):
                dx,dy=q[0]-p[0],q[1]-p[1];length=math.hypot(dx,dy)
                t=((x-p[0])*dx+(y-p[1])*dy)/length
                off=abs((x-p[0])*dy-(y-p[1])*dx)/length
                if off<.001 and 1.6<t<length-1.6:
                    s['openings'].append(dict(id='side_'+socket['id'],edge=edge,center=t,width=3,height=2.8));break
            else:raise RuntimeError('No authored side wall for '+s['id'])
            rooms.append(s)
        # Independent plaster skins for the main shell; names retain the _Tiles suffix.
        for variant in (1,2):
            skin=copy.deepcopy(r);skin.update(id=r['id']+'_Skin'+str(variant),surface_variant=variant,export_kinds=['Tiles'])
            rooms.append(skin)
cfg={k:copy.deepcopy(v) for k,v in repairs.items() if k not in ('rooms','links')}
cfg.update(seed=20260924,rooms=rooms,links=[])
(ROOT/'Config/rooms.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/main-rooms.json').write_text(json.dumps(main,ensure_ascii=False,indent=2),encoding='utf-8')
print('VARIANT_RECIPES_WRITTEN',len(main),len(rooms))
