"""Create explicit bindings from the read-back luminous surfaces."""
from pathlib import Path
import json,math,copy,runpy
import numpy as np
ROOT=Path(__file__).resolve().parent
G=json.loads((ROOT/'Receipts/geometry.json').read_text('utf8'))
F=json.loads((ROOT/'Receipts/fixtures.json').read_text('utf8'))
policy=runpy.run_path(str(ROOT/'recipe.py'))['effective_policy']
def luminous(f):
    return any(k in f['material'].lower() for k in ('warmglass','coolglass','cooltube','warmtube','lampglass','diffuser','glow','lampbulb','workshop_lamp','wstools_lens'))
def fields(f,kind='rect',normal=None):
    n=np.array(normal if normal is not None else [0,0,-1.],dtype=float);n/=np.linalg.norm(n)
    pts=np.array(f['points']);center=np.array(f['center']);front=(pts@n).max()
    face=center+n*(front-center@n);position=face+n
    pitch=math.degrees(math.asin(n[2]));yaw=math.degrees(math.atan2(n[1],n[0]))
    down=n[2]<-.9999;roll=90 if down else 0
    if down:width,height=f['size'][:2]
    else:
        right=np.array([-n[1],n[0],0.]);right/=np.linalg.norm(right);up=np.cross(n,right)
        width=np.ptp(pts@right);height=np.ptp(pts@up)
        if 'PassageDiffusers_UV2' in f['mesh']:width*=.707; height*=.707
    props=dict(type=kind,position=position.tolist(),pitch=pitch,yaw=yaw,roll=roll,
        source_width_cm=float(width),source_height_cm=float(height)) if kind=='rect' else dict(type=kind,position=position.tolist(),pitch=-90.,source_radius=1.,source_length=0.)
    return dict(fields=props,mesh=f['mesh'],face_center_cm=face.tolist(),normal=n.tolist(),
        fixture_size_cm=f['size'],emitter_clearance_cm=1.,reason='Align emitter to imported luminous face; keep the existing light budget and fault state.')

def main():
    result=dict(revision='dungeon_fixture_faces_20261009',modules={},fixed={},additional_parts={},splits={},portal_variants_checked=[])
    for m in G['catalog']['modules']:
        key=m['id']
        if key=='FacilityReceptionHall' or not m['lights']:continue
        candidates=[f for f in F['modules'][key] if luminous(f)]
        if key=='FacilityTransit':
            for gate,themes in F['variants'].items():
                reference=[f for f in themes['freight'] if 'Diffusers' in f['mesh']]
                for theme,fs in themes.items():
                    lamps=[f for f in fs if 'Diffusers' in f['mesh']]
                    if len(lamps)!=3:raise RuntimeError('Portal fixture count: '+theme)
                    for f in reference:
                        pair=min(lamps,key=lambda ff:math.dist(ff['center'],f['center']))
                        if math.dist(f['center'],pair['center'])>.05 or math.dist(f['size'],pair['size'])>.05:raise RuntimeError('Portal variants have different light faces')
                    result['portal_variants_checked'].append(gate+'/'+theme)
                candidates+=reference
        rows=[];used=set()
        for i,l in enumerate(m['lights']):
            if l.get('fill_only') or (key=='EcoNursery' and i in (15,16)) or (key=='EcoHydroponics' and i in (16,17)):
                rows.append(dict(anchor_cm=l['position'],remove=True,reason='Remove floating omnidirectional fill with no physical light fixture.'));continue
            if key.startswith('RouteRamp') and i==1:
                # The landing ceiling is floor + 280 cm. This existing fitting
                # has a hanger top at local +21 cm and glass at -8..-4 cm.
                pos=[l['position'][0],l['position'][1],l['position'][2]+24]
                mesh='/Game/Dungeons/IndustrialV1/Meshes/SM_CeilingLamp_Cool'
                part=dict(mesh=mesh,position=pos,scale=[1,1,1],yaw=0,collision=False,affects_navigation=False,cast_shadow=True,materials=[],fluid=False,fixture_lighting_revision=result['revision'])
                result['additional_parts'][key]=[part]
                section=next(s for s in G['meshes'][mesh] if 'CoolTube' in s['material'])
                pts=np.array(section['vertices'])+np.array(pos);lo=pts.min(0);hi=pts.max(0)
                f=dict(mesh=mesh,points=pts.tolist(),center=((lo+hi)/2).tolist(),size=(hi-lo).tolist())
                b=fields(f);b['reason']='Add a ceiling-mounted fitting to the existing landing light; retain its intensity, range and source count.'
            else:
                idx,f=min(enumerate(candidates),key=lambda v:math.dist(l['position'],v[1]['center']))
                if idx in used:raise RuntimeError('Two source entries matched one fitting: '+key+'/'+str(i))
                used.add(idx)
                distance=math.dist(l['position'],f['center'])
                if distance>50 and not(key=='FacilityTransit' and i in (22,24,26)):raise RuntimeError('Unmatched fixture '+key+'/'+str(i)+': '+str(distance))
                kind=policy(m,i,l)['kind']
                normal=None
                if key=='FacilityEntrancePassage' and i in (2,3):normal=[1 if f['center'][0]<0 else -1,-.95/3,0]
                if key=='AbandonedTransitStation' and l.get('id')=='StationWorkshop.BenchTask':normal=[-.6152612426252373,.10937977646670938,-.7806981925323904]
                b=fields(f,'spot' if kind=='spot' else 'rect',normal)
                if key=='FacilityTransit' and i in (22,24,26):
                    # One centered point used to sit between two tunnel fittings.
                    # Divide its flux across the actual pair without a brightness increase.
                    other=min((ff for j,ff in enumerate(candidates) if j!=idx),key=lambda ff:math.dist(l['position'],ff['center']))
                    b['intensity_scale']=.5
                    extra=fields(other);extra['intensity_scale']=.5;extra['source_index']=i
                    result['splits'].setdefault(key,[]).append(extra)
                    b['reason']='Split midpoint tunnel light across both existing fixtures, conserving the original downward light output.'
            b['anchor_cm']=l['position'];b['original_id']=l.get('id');rows.append(b)
        result['modules'][key]=rows
    fixed=[f for f in F['fixed'] if luminous(f)]
    for actor in G['fixed']:
        for l in actor['lights']:
            f=min(fixed,key=lambda f:math.dist(l['position'],f['center']))
            if math.dist(l['position'],f['center'])>20:raise RuntimeError('Unmatched fixed light: '+actor['label'])
            if 'WorkbenchKit' in actor['label']:
                b=fields(f,'spot',l['forward']);b['fields'].update(position=l['position'],pitch=l['rotation'][0],yaw=l['rotation'][1],roll=l['rotation'][2],source_radius=l['source_radius'],source_length=l['source_length'])
                b.update(preserve_transform=True,reason='Existing task spotlight is aligned with its exposed bulb and desk target; retain its authored pose.')
            elif 'Sconce' in actor['label']:
                b=fields(f,'point');b['fields'].update(position=l['position'],pitch=0,yaw=0,source_radius=3.,source_length=0.)
                b.update(preserve_transform=True,reason='Exposed cylindrical sconce bulb intentionally radiates outward; constrain source radius inside glass and remove line-source length.')
            else:b=fields(f)
            b.update(anchor_cm=l['position'],original_type=l['type'])
            result['fixed'][actor['label']]=b
    (ROOT/'Config').mkdir(exist_ok=True)
    (ROOT/'Config/bindings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('BINDINGS',sum(len(v) for v in result['modules'].values()),'module sources;',len(result['fixed']),'fixed;',len(result['portal_variants_checked']),'portal variants')

if __name__=='__main__':main()
