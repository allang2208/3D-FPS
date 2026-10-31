"""Dimensioned production placements; all distances in centimetres unless suffixed."""
from pathlib import Path
from itertools import product
import json,math,collections
R=Path(__file__).resolve().parent;PROJECT=R.parents[1]
BASE='/Game/Props/CyberpunkExteriorUpgrade20261025'
HERO=[36,38,41,43,44,46,47,50,52,55,57,64]
MIDDLE=[37,40,42,45,48,51,54,56,59,62]
SIDES=[22,24,25,26,27,28,29,31,32,33,34,65,66,67,68,69,70,71,72,73,75,77]
PROTECTED=[30,35,39,49,53,58,61,63]
PROTOTYPES=['BPP_CHA_Ref_N1','BPP_CHB_Ref_A1_N1','BPP_CHC_Ref_A1_N1','BPP_CHE_Ref_A1_N1','BPP_CHF_Ref_A1_N1','BPP_CHH_Ref_A1_N1','BPP_CHI_Ref_A1_N1','BPP_NYH_Ref_N1','BPP_SFE_Ref_N1','BPP_SFJ_Ref_N1']
GROUNDS=dict(BPP_CHA_Ref_N1='BPP_CHA_Ref_Level01_N1',BPP_CHB_Ref_A1_N1='BPP_CHB_Ref_A1_Level01_N1',BPP_CHE_Ref_A1_N1='BPP_CHE_Ref_A1_Level01_N1',BPP_CHF_Ref_A1_N1='BPP_CHF_Ref_A1_Level01_N1',BPP_CHH_Ref_A1_N1='BPP_CHH_Ref_A1_Level01_N1',BPP_CHI_Ref_A1_N1='BPP_CHI_Ref_A1l_Level01_N1')

def rotate(v,q):
    x,y,z=v;a,b,c,w=q;t=[2*(b*z-c*y),2*(c*x-a*z),2*(a*y-b*x)]
    return [x+w*t[0]+b*t[2]-c*t[1],y+w*t[1]+c*t[0]-a*t[2],z+w*t[2]+a*t[1]-b*t[0]]

def transform(v,t):return [a+b for a,b in zip(rotate([a*b for a,b in zip(v,t['s'])],t['q']),t['p'])]
def corners(b):return product(*zip(b['min'],b['max']))
def box_of(points):
    p=list(points);return dict(min=[min(v[i] for v in p) for i in range(3)],max=[max(v[i] for v in p) for i in range(3)])
def yaw(v,angle):
    c=math.cos(math.radians(angle));s=math.sin(math.radians(angle));return [v[0]*c-v[1]*s,v[0]*s+v[1]*c,v[2]]
def world(p):return [(-p[0]+10)*125,(p[1]-615)*125,(p[2]-90)*125]

def main():
    d=json.loads((R/'sources.json').read_text());rows=json.loads((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json').read_text())['buildings']
    if d.get('stage')!='production_inputs_ready':raise RuntimeError('Complete source and ground-floor authoring inputs first')
    definitions={}
    for name in PROTOTYPES:
        parts=[name]+([GROUNDS[name]] if name in GROUNDS else [])
        allpoints=[];roofs=[]
        for part in parts:
            for c in d['assemblies'][part]['components']:
                mesh=d['meshes'][c['mesh']]
                for t in c['instances']:
                    points=[transform(v,t) for v in corners(mesh)];allpoints.extend(points)
                    # A real horizontal roof plane, not the highest vertex of the building.
                    if 'SM_Plane' in c['mesh'] and any('/Roof/' in (m or '') for m in c['materials']) and abs(rotate([0,0,1],t['q'])[2])>.999:
                        b=box_of(points);size=[b['max'][i]-b['min'][i] for i in range(3)]
                        if min(size[:2])>650 and size[2]<30:roofs.append(dict(bounds=b,component=c['component'],part=part))
        definitions[name]=dict(parts=parts,bounds=box_of(allpoints),roofs=sorted(roofs,key=lambda r:r['bounds']['max'][2],reverse=True))
    counts=collections.Counter();placements=[];previous=None
    for i in sorted(HERO+MIDDLE+SIDES):
        r=rows[i];targetH=r['authored_height']*125;limit=[r['width']*1.10*125,r['depth']*1.08*125];options=[]
        for name,definition in definitions.items():
            for angle in (0,90,180,270):
                b=box_of(yaw(v,angle) for v in corners(definition['bounds']));sz=[b['max'][j]-b['min'][j] for j in range(3)]
                fit=min(limit[0]/sz[0],limit[1]/sz[1]);scale=min(1.4,fit,targetH/sz[2])
                if scale<.82:continue
                score=abs(math.log(sz[2]*scale/targetH))*4+abs(math.log(scale/1.2))*.25+abs(math.log(sz[0]*scale/limit[0]))*.18+counts[name]*.055+(name==previous)*.24
                score+=((i*17+angle//90*7+PROTOTYPES.index(name)*11)%19)*.001
                options.append((score,name,angle,scale,b,sz))
        if not options:raise RuntimeError('No proportion-preserving fit for '+str(i))
        _,name,angle,scale,b,sz=min(options,key=lambda p:p[0]);counts[name]+=1;previous=name
        front=world((r['x'],r['y']-r['depth']*.565,5))
        loc=[front[0]-(b['min'][0]+b['max'][0])*.5*scale,front[1]-b['min'][1]*scale,front[2]-b['min'][2]*scale]
        placement=dict(id=f'BAY-B{i:04d}',index=i,zone='primary' if i in HERO else 'middle' if i in MIDDLE else 'side',prototype=name,parts=definitions[name]['parts'],yaw=angle,scale=scale,location=loc,source_bounds=definitions[name]['bounds'],world_bounds=dict(min=[loc[j]+b['min'][j]*scale for j in range(3)],max=[loc[j]+b['max'][j]*scale for j in range(3)]),old_layout=r,front_anchor=front,night_occupied_fraction=.40)
        roofs=definitions[name]['roofs']
        if roofs:
            roof=roofs[0];rb=roof['bounds'];center=[(rb['min'][j]+rb['max'][j])*.5 for j in range(3)];center[2]=rb['max'][2]
            rotated=yaw(center,angle)
            placement['service_roof']=dict(source=roof,center=[loc[j]+rotated[j]*scale for j in range(3)],yaw=angle,size=[(rb['max'][j]-rb['min'][j])*scale for j in range(2)])
        placements.append(placement)
    result=dict(version='ExteriorFab20261025',map='/Game/GameMaps/L_CyberpunkApartment',asset_root=BASE,placements=placements,prototypes={k:v for k,v in definitions.items() if counts[k]},prototype_counts=dict(counts),replaced_indices=sorted(HERO+MIDDLE+SIDES),affected_groups=sorted(set(p['old_layout']['group'] for p in placements)),preserved_ad_hosts=[dict(id=f'BAY-B{i:04d}',index=i,layout=rows[i]) for i in PROTECTED],preserved_landmarks=5,far_proxy_buildings=sum(r['group'].startswith('Far') for r in rows),new_tick_actors=0,new_realtime_lights=0)
    (R/'layout.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('EXTERIOR_LAYOUT_AUTHORED',len(placements),dict(counts),'roof anchors',sum('service_roof' in p for p in placements))
if __name__=='__main__':main()
