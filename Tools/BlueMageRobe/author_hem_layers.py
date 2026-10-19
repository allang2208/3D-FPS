"""Continuous foot/calf/low-thigh layers, with a separately deformable upper region.

No stair-only disks or disappearing calf sections. Source attributes and all
cross-boundary weights are interpolated at the same edge parameter.
"""
import json,copy
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/HemContinuity20261019';O=R/'Authored';O.mkdir(parents=True,exist_ok=True)
rows=[]
def blend(a,b,t):
    pairs=sorted(((k,a.get(k,0)*(1-t)+b.get(k,0)*t) for k in a.keys()|b.keys()),key=lambda x:-x[1])[:8]
    total=sum(w for _,w in pairs);return {k:w/total for k,w in pairs if w>1e-8}
for row in json.loads((R/'inputs.json').read_text())['rows']:
    d=json.loads(Path(row['file']).read_text());p=np.asarray(d['positions']);bones=d['bones'];byid={v['index']:n for n,v in bones.items()}
    length=float(np.mean([np.linalg.norm(np.array(bones['calf_'+s]['position'])-bones['foot_'+s]['position']) for s in ('l','r')]))
    ankle=max(bones['foot_'+s]['position'][2] for s in ('l','r'))+.15*length
    dims=json.loads((P/'SourceAssets/BlueMageRobe20261018/Authored/Body'/(row['profile']+'.json')).read_text())['cloth_dimensions']
    top=min(max(bones['calf_'+s]['position'][2] for s in ('l','r'))+.4*length,dims['waist_cm']-6*dims['scale'])
    def lower(n):
        while n in bones:
            if n in ('thigh_l','thigh_r'):return True
            if bones[n]['parent']<0:return False
            n=byid[bones[n]['parent']]
        return False
    names={n for n in bones if lower(n)}|{'pelvis'}
    mass=[sum(w for n,w in entry.items() if n in names) for entry in d['weights']]
    out={k:copy.deepcopy(d[k]) for k in ('positions','weights','bones','skeleton','material_slots','materials')}
    out.update(profile=row['key'],binding_source=row['source'],triangles=[],normals=[],uv=[],triangle_materials=[],contract='Continuous robe underlayer: original foot and ankle; full calf plus lower-thigh overlap; no visibility cut or ankle cap; upper region follows the local animated cloth envelope')
    slots={};edgecache={}
    def slot(m):
        if m not in slots:
            slots[m]=len(out['materials']);out['materials'].append(d['materials'][m]);out['material_slots'].append('RobeStairHidden_'+str(m))
        return slots[m]
    def cut(poly,z,keep_below):
        result=[]
        for i,(vi,uv,norm) in enumerate(poly):
            vj,uvj,nj=poly[(i+1)%len(poly)];a=np.asarray(out['positions'][vi]);b=np.asarray(out['positions'][vj]);inside=(a[2]<=z) if keep_below else (a[2]>=z)
            if inside:result.append((vi,uv,norm))
            other=(b[2]<=z) if keep_below else (b[2]>=z)
            if inside!=other:
                t=float((z-a[2])/(b[2]-a[2]));key=(round(z,6),*sorted((vi,vj)))
                if key not in edgecache:
                    edgecache[key]=len(out['positions']);out['positions'].append((a+(b-a)*t).tolist());out['weights'].append(blend(out['weights'][vi],out['weights'][vj],t))
                n=norm+(nj-norm)*t;n/=max(np.linalg.norm(n),1e-10);result.append((edgecache[key],uv+(uvj-uv)*t,n))
        return result
    def emit(poly,m):
        for j in range(1,len(poly)-1):
            tri=[poly[0],poly[j],poly[j+1]];out['triangles'].append([x[0] for x in tri]);out['uv'].append([x[1].tolist() for x in tri]);out['normals'].append([x[2].tolist() for x in tri]);out['triangle_materials'].append(m)
    for fi,face in enumerate(d['triangles']):
        poly=[(vi,np.asarray(d['uv'][fi][ci]),np.asarray(d['normals'][fi][ci])) for ci,vi in enumerate(face)];m=d['triangle_materials'][fi]
        eligible=row['kind']!='skin' or (sum(mass[v] for v in face)/3>.35 and max(p[face,2])<dims['waist_cm'])
        if not eligible:emit(poly,m);continue
        poly=cut(poly,top,True)
        if not poly:continue
        emit(cut(poly,ankle,True),m)
        upper=cut(poly,ankle,False)
        if len(upper)>=3:emit(upper,slot(m))
    # Discard removed upper-leg vertices, keeping the same shared edge indices.
    used=sorted({v for tri in out['triangles'] for v in tri});remap={v:i for i,v in enumerate(used)}
    out['positions']=[out['positions'][v] for v in used];out['weights']=[out['weights'][v] for v in used];out['triangles']=[[remap[v] for v in tri] for tri in out['triangles']]
    file=O/(row['key']+'.json');file.write_text(json.dumps(out,separators=(',',':')))
    deformable=sum(m>=len(d['materials']) for m in out['triangle_materials'])
    rows.append(dict(**row,authored=str(file),cut_cm=ankle,upper_overlap_cm=top,hidden_source_triangles=deformable,cap_triangles=0,triangles=len(out['triangles']),materials=out['materials'],material_slots=out['material_slots']))
    print('ROBE_HEM_LAYER_AUTHORED',row['key'],len(out['triangles']),flush=True)
(R/'authored.json').write_text(json.dumps(dict(rows=rows,runtime_tested=False),indent=2))
