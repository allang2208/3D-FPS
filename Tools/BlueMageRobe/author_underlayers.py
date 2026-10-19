"""Derive robe-only inner layers while retaining the complete lower legs."""
import json,copy
from pathlib import Path
import numpy as np
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018');F=R/'LegFit20261019';OUT=F/'Authored';OUT.mkdir(exist_ok=True,parents=True)
inputs=json.loads((F/'inputs.json').read_text(encoding='utf-8'));report=[]
def mix_weights(a,b,t):
    w={n:a.get(n,0)*(1-t)+b.get(n,0)*t for n in a.keys()|b.keys()};pairs=sorted(((n,v) for n,v in w.items() if v>1e-8),key=lambda x:-x[1])[:8];total=sum(v for _,v in pairs);return {n:v/total for n,v in pairs}
for row in inputs['rows']:
    d=json.loads(Path(row['file']).read_text(encoding='utf-8'));dims=json.loads((R/'Authored/Body'/(row['profile']+'.json')).read_text())['cloth_dimensions'];p=np.array(d['positions']);bones=d['bones'];byid={v['index']:n for n,v in bones.items()}
    # Keep the calf through the knee joint, with a small overlap into the robe.
    # A hem-relative cut incorrectly removed almost the entire lower leg.
    cut=max(bones[n]['position'][2] for n in ('calf_l','calf_r'))+2*dims['scale'];changed=False
    def lower(n):
        while n in bones:
            if n in ('thigh_l','thigh_r'):return True
            if bones[n]['parent']<0:return False
            n=byid[bones[n]['parent']]
        return False
    lower_names={n for n in bones if lower(n)}|{'pelvis'};mass=np.array([sum(v for n,v in w.items() if n in lower_names) for w in d['weights']]);out={k:copy.deepcopy(d[k]) for k in ('bones','skeleton','material_slots')};out.update(profile=row['key'],binding_source=row['source'],positions=[],weights=[],triangles=[],normals=[],uv=[],triangle_materials=[],contract='Robe inner layer v3: preserve complete native calves, knee overlap, trouser cuffs and footwear; conceal only covered upper legs; original item unchanged')
    verts={}
    def vertex(k,pos,w):
        if k not in verts:verts[k]=len(out['positions']);out['positions'].append(list(map(float,pos)));out['weights'].append(w)
        return verts[k]
    for fi,face in enumerate(d['triangles']):
        clip=row['kind']!='skin' or (float(mass[face].mean())>.35 and max(p[face,2])<dims['waist_cm'])
        changed=changed or (clip and max(p[face,2])>cut)
        poly=[]
        for ci,vi in enumerate(face):
            pos=p[vi];uv=np.array(d['uv'][fi][ci]);normal=np.array(d['normals'][fi][ci]);ni=(ci+1)%3;vj=face[ni];inside=not clip or pos[2]<=cut
            if inside:poly.append((vertex(('v',vi),pos,d['weights'][vi]),uv,normal))
            if clip and inside!=(p[vj,2]<=cut):
                t=(cut-pos[2])/(p[vj,2]-pos[2]);q=pos+(p[vj]-pos)*t;k=('edge',*sorted((vi,vj)));w=mix_weights(d['weights'][vi],d['weights'][vj],t);n=normal+(np.array(d['normals'][fi][ni])-normal)*t;n/=max(np.linalg.norm(n),1e-12)
                poly.append((vertex(k,q,w),uv+(np.array(d['uv'][fi][ni])-uv)*t,n))
        for i in range(1,len(poly)-1):
            tri=[poly[0],poly[i],poly[i+1]];out['triangles'].append([v[0] for v in tri]);out['uv'].append([v[1].tolist() for v in tri]);out['normals'].append([v[2].tolist() for v in tri]);out['triangle_materials'].append(d['triangle_materials'][fi])
    file=OUT/(row['key']+'.json');file.write_text(json.dumps(out,separators=(',',':')),encoding='utf-8');report.append(dict(**row,authored=str(file),cut_cm=cut,geometry_changed=bool(changed),source_triangles=len(d['triangles']),remaining_triangles=len(out['triangles']),materials=d['materials']))
    print('ROBE_INNER_LAYER_AUTHORED',row['kind'],row['source'].rsplit('/',1)[-1],len(d['triangles']),'->',len(out['triangles']),flush=True)
(F/'authored.json').write_text(json.dumps(dict(rows=report,runtime_tested=False),indent=2),encoding='utf-8')
