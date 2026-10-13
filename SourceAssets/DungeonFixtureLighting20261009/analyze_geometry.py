"""Offline, per-emitter inventory from the imported mesh sections."""
from pathlib import Path
import json
import math
import numpy as np

ROOT=Path(__file__).resolve().parent
def islands(section):
    verts=np.array(section['vertices']);tris=section['triangles']
    if not len(verts):return []
    _,labels=np.unique(np.round(verts,3),axis=0,return_inverse=True)
    parents=list(range(max(labels)+1))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i in range(0,len(tris),3):
        a,b,c=(find(labels[j]) for j in tris[i:i+3]);parents[b]=a;parents[c]=a
    groups={}
    for i,k in enumerate(labels):groups.setdefault(find(k),[]).append(i)
    return [verts[g] for g in groups.values()]

def components(sections):
    result=[]
    for section in sections:
        if 'Reflector' in section['material']:continue
        chunks=islands(section)
        # Twin fluorescent tubes and lens pieces form one physical fitting.
        changed=True
        while changed:
            changed=False
            for i in range(len(chunks)):
                lo,hi=chunks[i].min(0),chunks[i].max(0)
                for j in range(i+1,len(chunks)):
                    gap=np.maximum(0,np.maximum(lo-chunks[j].max(0),chunks[j].min(0)-hi))
                    if np.linalg.norm(gap)<14:
                        chunks[i]=np.concatenate([chunks[i],chunks.pop(j)]);changed=True;break
                if changed:break
        for points in chunks:result.append(dict(material=section['material'],points=points))
    return result

def transform(row,p):
    return np.array(p['position'])+(row*np.array(p['scale']))@np.array(p['axes'])

def fixtures(parts,library):
    out=[]
    for part_i,p in enumerate(parts):
        for n,c in enumerate(library[p['mesh']]):
            pts=transform(c['points'],p);lo=pts.min(0);hi=pts.max(0)
            out.append(dict(mesh=p['mesh'],material=c['material'],part=part_i,island=n,lo=lo.tolist(),hi=hi.tolist(),
                center=((lo+hi)/2).tolist(),size=(hi-lo).tolist(),points=pts.tolist()))
    return out

def main():
    geo=json.loads((ROOT/'Receipts/geometry.json').read_text('utf8'))
    lib={p:components(ss) for p,ss in geo['meshes'].items()}
    modules={key:fixtures(parts,lib) for key,parts in geo['module_transforms'].items()}
    variants={key:{theme:fixtures(parts,lib) for theme,parts in themes.items()} for key,themes in geo['variants'].items()}
    fixed=[]
    for actor in geo['fixed']:
        for f in fixtures(actor['meshes'],lib):f['actor']=actor['label'];fixed.append(f)
    result=dict(modules=modules,variants=variants,fixed=fixed)
    (ROOT/'Receipts/fixtures.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf8')
    report=[]
    for module in geo['catalog']['modules']:
        if module['id']=='FacilityReceptionHall':continue
        candidates=modules[module['id']]
        if module['id']=='FacilityTransit':
            for gate in variants.values():candidates=candidates+next(iter(gate.values()))
        for i,l in enumerate(module['lights']):
            ordered=sorted(enumerate(candidates),key=lambda item:math.dist(l['position'],item[1]['center']))[:3]
            near=[dict(distance=round(math.dist(l['position'],f['center']),2),fixture_index=idx,
                mesh=f['mesh'].split('/')[-1],center=[round(n,2) for n in f['center']],size=[round(n,2) for n in f['size']]) for idx,f in ordered]
            report.append(dict(module=module['id'],index=i,id=l.get('id'),position=l['position'],nearest=near))
    for actor in geo['fixed']:
        for l in actor['lights']:
            ordered=sorted(enumerate(fixed),key=lambda item:math.dist(l['position'],item[1]['center']))[:3]
            report.append(dict(module='FixedStart',id=actor['label'],position=l['position'],nearest=[dict(distance=round(math.dist(l['position'],f['center']),2),fixture_index=idx,mesh=f['mesh'].split('/')[-1],center=f['center'],size=f['size']) for idx,f in ordered]))
    (ROOT/'Receipts/matches.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    for key,fs in modules.items():print(key,len(fs),'emissive components')
    for r in report:
        if not r['nearest'] or r['nearest'][0]['distance']>50:print('OFFSET',r)

if __name__=='__main__':main()
