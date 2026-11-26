"""Restore native wrist skin under the robe cuff by partitioning existing faces."""
import copy, json
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/BlueMageRobe20261018'
OUT=BASE/'WristContinuity20261020';(OUT/'Authored').mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
mapping=cfg['items']['ue_blue_mage_robe']['underlayer_meshes']
rows=[]
def weights(a,b,t):
    values=sorted(((n,a.get(n,0)*(1-t)+b.get(n,0)*t) for n in a.keys()|b.keys()),key=lambda pair:-pair[1])[:8]
    total=sum(v for _,v in values)
    return {n:float(v/total) for n,v in values if v>1.e-8}
for row in json.loads((BASE/'TurnLegContinuity20261020/authored.json').read_text())['rows']:
    if row['kind']!='skin':continue
    d=json.loads(Path(row['authored']).read_text())
    out=copy.deepcopy(d)
    for key in ('triangles','normals','uv','triangle_materials'):out[key]=[]
    arm_slot=d['material_slots'].index('SkinArms')
    hand_slot=d['material_slots'].index('SkinHands')
    p=np.asarray(d['positions']);frames={};cache={};reassigned=0;split=0
    for side in ('l','r'):
        wrist=np.array(d['bones']['hand_'+side]['position'])
        elbow=np.array(d['bones']['lowerarm_'+side]['position'])
        axis=wrist-elbow;length=np.linalg.norm(axis);axis/=length
        # Native forearm proportion, capped to the cuff's covered interval.
        overlap=float(np.clip(length*.18,3.5,4.5))
        frames[side]=(wrist,axis,overlap)
    def cut(poly,side,distal):
        wrist,axis,overlap=frames[side];result=[]
        for i,(vi,uv,normal) in enumerate(poly):
            vj,uvj,nj=poly[(i+1)%len(poly)]
            a=np.array(out['positions'][vi]);b=np.array(out['positions'][vj])
            da=float((a-wrist)@axis+overlap);db=float((b-wrist)@axis+overlap)
            inside=da>=0 if distal else da<=0
            other=db>=0 if distal else db<=0
            if inside:result.append((vi,uv,normal))
            if inside!=other:
                t=da/(da-db);key=(side,*sorted((vi,vj)))
                if key not in cache:
                    cache[key]=len(out['positions'])
                    out['positions'].append((a+(b-a)*t).tolist())
                    out['weights'].append(weights(out['weights'][vi],out['weights'][vj],t))
                n=normal+(nj-normal)*t;n/=max(np.linalg.norm(n),1.e-12)
                result.append((cache[key],uv+(uvj-uv)*t,n))
        return result
    def emit(poly,slot):
        for j in range(1,len(poly)-1):
            triangle=[poly[0],poly[j],poly[j+1]]
            out['triangles'].append([v[0] for v in triangle])
            out['uv'].append([v[1].tolist() for v in triangle])
            out['normals'].append([v[2].tolist() for v in triangle])
            out['triangle_materials'].append(slot)
    for fi,face in enumerate(d['triangles']):
        slot=d['triangle_materials'][fi]
        poly=[(vi,np.array(d['uv'][fi][ci]),np.array(d['normals'][fi][ci])) for ci,vi in enumerate(face)]
        if slot!=arm_slot:
            emit(poly,slot);continue
        side=max(('l','r'),key=lambda s:sum(v for vi in face for n,v in d['weights'][vi].items() if n.endswith('_'+s)))
        wrist,axis,overlap=frames[side]
        distance=(p[face]-wrist)@axis+overlap
        if distance.max()<=0:
            emit(poly,slot);continue
        if distance.min()>=0:
            emit(poly,hand_slot);reassigned+=1;continue
        emit(cut(poly,side,False),arm_slot);emit(cut(poly,side,True),hand_slot)
        split+=1
    out['contract']='Robe inner body: native wrist and palm-root faces remain visible with hand coverage; forearm overlap inside cuff; complete hem geometry and existing lower-layer sections retained'
    file=OUT/'Authored'/(row['key']+'.json')
    file.write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
    rows.append(dict(key=row['key'],profile=row['profile'],original=row['original'],
        current_mesh=mapping[row['original']],file=str(file),material_slots=d['material_slots'],
        restored_faces=reassigned,split_boundary_faces=split,
        wrist_overlap_cm={s:frames[s][2] for s in frames},
        source_triangles=len(d['triangles']),triangles=len(out['triangles'])))
    print('ROBE_WRIST_AUTHORED',row['key'],reassigned,split,flush=True)
(OUT/'authored.json').write_text(json.dumps(dict(completed=True,rows=rows,runtime_tested=False),indent=2),encoding='utf-8')
