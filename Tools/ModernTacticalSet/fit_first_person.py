"""Own TS01 V7 surface fit; original V7 meshes and animations remain inputs."""
import ast,copy,gc,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/Integration';D=R/'Delivery'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
# Reuse the same native bone/normal transport functions without running the
# unrelated body, trouser and helmet production stages.
tree=ast.parse((P/'Tools/ModernTacticalSet/derive.py').read_text(encoding='utf-8'))
helpers=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['warp_gloves','transport_normals','subset']],type_ignores=[])
exec(compile(helpers,'ts01_native_transport','exec'))
capture=read(R/'captured.json');manifest=read(R/'derived.json');m4=read(R/'Inputs/Gloves_M4.json')
old=warp_gloves(read(D/'gloves_foundation_Jason.json'),m4)
details=warp_gloves(read(D/'gloves_details_Jason.json'),m4)
fitted=P/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored'
canonical=read(fitted/'M4.json');bone_ids={b['name']:b['index'] for b in m4['bones']}

def native_shell(data,native):
    names={b['name']:b['index'] for b in native['bones']}
    out={k:copy.deepcopy(data[k]) for k in ['positions','triangles','normals','uv']}
    out['bones']=native['bones'];out['source']=native['source']
    out['weights']=[[[names[n],w] for n,w in ws.items()] for ws in data['weights']]
    out['material_slots']=['TS01_RangerNylon','TS01_CharcoalLeather','TS01_CharcoalStretch']
    cp=np.asarray(data['canonical_positions']);cn=np.asarray(data['canonical_normals']).mean(axis=1);t=np.asarray(data['triangles']);c=cp[t].mean(axis=1)
    mats=np.zeros(len(t),int)
    for side in ['l','r']:
        bp={b['name']:np.array(b['position']) for b in m4['bones']};wrist=bp['hand_'+side];forward=bp['middle_01_'+side]-wrist;forward/=np.linalg.norm(forward)
        across=bp['index_01_'+side]-bp['pinky_01_'+side];normal=np.cross(across,forward);normal/=np.linalg.norm(normal)
        # Identify the back from the authored TS01 protection parts nearby.
        pp=np.asarray(details['positions']);dt=np.asarray(details['triangles']);dm=np.asarray(details['triangle_materials']);guard=np.unique(dt[dm==details['material_slots'].index('TS01_MattePolymer')]);points=pp[guard];closest=points[np.argsort(np.linalg.norm(points-wrist,axis=1))[:160]].mean(axis=0)
        if np.dot(closest-wrist,normal)<0:normal=-normal
        selected=(c[:,0]-wrist[0])**2<(c[:,0]-bp['hand_'+('r' if side=='l' else 'l')][0])**2
        mats[selected&(cn@normal<.05)]=1
        mats[selected&((c-wrist)@forward<.3)]=2
    out['triangle_materials']=mats.tolist()
    # Keep a consistent physical textile density across the native hand UV seams.
    uv=[]
    for face,n in zip(t,cn):
        axes=[i for i in range(3) if i!=int(np.argmax(abs(n)))];uv.append((cp[face][:,axes]/8).tolist())
    out['uv']=uv
    return out

base=native_shell(canonical,m4)
def regions(data):
    names=[b['name'] for b in data['bones']];labels=[]
    for ws in data['weights']:
        mass={}
        for bi,w in ws:
            n=names[bi];side=n[-1];part=next((f for f in ['thumb','index','middle','ring','pinky'] if n.startswith(f+'_')),'hand');label=part+'_'+side;mass[label]=mass.get(label,0)+w
        labels.append(max(mass,key=mass.get))
    return np.array(labels)

def normals(data):
    out=np.zeros((len(data['positions']),3));t=np.array(data['triangles']);n=np.array(data['normals'])
    for k in range(3):np.add.at(out,t[:,k],n[:,k])
    out/=np.maximum(np.linalg.norm(out,axis=1,keepdims=True),1e-10);return out

op=np.array(old['positions']);bp=np.array(base['positions']);dp=np.array(details['positions']);on=normals(old);bn=normals(base)
ol=regions(old);bl=regions(base);dl=regions(details);new=dp.copy();new_weights=copy.deepcopy(details['weights'])
for label in sorted(set(dl)):
    oi=np.flatnonzero(ol==label);bi=np.flatnonzero(bl==label);di=np.flatnonzero(dl==label)
    if not len(oi) or not len(bi):raise RuntimeError('Missing native finger surface '+label)
    distances,near=cKDTree(bp[bi]).query(op[oi],k=min(24,len(bi)))
    indices=bi[near];score=distances+np.maximum(0,.45-(on[oi,None,:]*bn[indices]).sum(axis=2))*6
    pick=indices[np.arange(len(oi)),np.argmin(score,axis=1)];delta=bp[pick]-op[oi]
    dist,neighbors=cKDTree(op[oi]).query(dp[di],k=min(8,len(oi)));weights=1/np.maximum(dist,.08)**3;weights/=weights.sum(axis=1,keepdims=True)
    new[di]+=(delta[neighbors]*weights[:,:,None]).sum(axis=1)
    for vi,rows,fac in zip(di,pick[neighbors],weights):
        merged={}
        for ti,w in zip(rows,fac):
            for bone,value in base['weights'][int(ti)]:merged[bone]=merged.get(bone,0)+w*value
        ws=sorted(merged.items(),key=lambda x:-x[1])[:8];total=sum(w for b,w in ws);new_weights[vi]=[[b,float(w/total)] for b,w in ws]
details['positions']=new.tolist();details['weights']=new_weights;transport_normals(details,dp)

def add_curved_panel(side,palm=False):
    positions=np.asarray(base['positions']);norm=normals(base);bones={b['name']:np.array(b['position']) for b in base['bones']}
    wrist=bones['hand_'+side];forward=bones['middle_01_'+side]-wrist;forward/=np.linalg.norm(forward)
    across=bones['index_01_'+side]-bones['pinky_01_'+side];across-=forward*np.dot(across,forward);across/=np.linalg.norm(across)
    normal=np.cross(across,forward);normal/=np.linalg.norm(normal)
    t=np.asarray(details['triangles']);m=np.asarray(details['triangle_materials']);points=np.asarray(details['positions'])[np.unique(t[m==details['material_slots'].index('TS01_MattePolymer')])]
    guard=points[np.argsort(np.linalg.norm(points-wrist,axis=1))[:160]].mean(axis=0)
    if np.dot(guard-wrist,normal)<0:normal=-normal
    if palm:normal=-normal
    local=np.column_stack([(positions-wrist)@across,(positions-wrist)@forward,(positions-wrist)@normal])
    ids=np.flatnonzero((norm@normal>.30)&(np.linalg.norm(positions-wrist,axis=1)<11))
    tree=cKDTree(local[ids,:2]);nu,nv=22,24;points=[];ws=[]
    for v in np.linspace(0,1,nv+1):
        width=(1.65 if palm else 2.45)*(.83+.17*math.sin(math.pi*v))
        y=(1.7+3.4*v) if palm else (.7+3.8*v)
        for u in np.linspace(-1,1,nu+1):
            x=u*width;dist,near=tree.query([x,y],k=8);idx=ids[near];w=1/np.maximum(dist,.1)**3;w/=w.sum()
            height=float(local[idx,2]@w)+(.095 if palm else .14)
            points.append(wrist+across*x+forward*y+normal*height)
            merged={}
            for i,fac in zip(idx,w):
                for bi,weight in base['weights'][int(i)]:merged[bi]=merged.get(bi,0)+fac*weight
            pairs=sorted(merged.items(),key=lambda x:-x[1])[:8];total=sum(w for bi,w in pairs);ws.append([[bi,float(w/total)] for bi,w in pairs])
    outer=np.array(points);inner=outer-normal*.07;points=np.concatenate([outer,inner]);count=len(outer);faces=[];uv=[]
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i;quad=[a,a+1,a+nu+2,a+nu+1]
            for f in [[quad[0],quad[1],quad[2]],[quad[0],quad[2],quad[3]]]:
                if np.dot(np.cross(points[f[1]]-points[f[0]],points[f[2]]-points[f[0]]),normal)>0:f=f[::-1]
                faces.append(f);faces.append([v+count for v in f[::-1]])
    border=list(range(nu+1))+[j*(nu+1)+nu for j in range(1,nv+1)]+list(range(nv*(nu+1)+nu-1,nv*(nu+1)-1,-1))+[j*(nu+1) for j in range(nv-1,0,-1)]
    for a,b in zip(border,border[1:]+border[:1]):faces.extend([[a,b,b+count],[a,b+count,a+count]])
    material='TS01_CharcoalLeather' if palm else 'TS01_RangerRipstop'
    if material not in details['material_slots']:details['material_slots'].append(material)
    start=len(details['positions']);details['positions']+=points.tolist();details['weights']+=ws+copy.deepcopy(ws)
    smooth_normals=np.zeros_like(points)
    for f in faces:
        n=-np.cross(points[f[1]]-points[f[0]],points[f[2]]-points[f[0]])
        for i in f:smooth_normals[i]+=n
    smooth_normals/=np.maximum(np.linalg.norm(smooth_normals,axis=1,keepdims=True),1e-12)
    for f in faces:
        details['triangles'].append([i+start for i in f]);details['normals'].append(smooth_normals[f].tolist());details['uv'].append([[(points[i]-wrist)@across/8,(points[i]-wrist)@forward/8] for i in f]);details['triangle_materials'].append(details['material_slots'].index(material))

import math
for side in ['l','r']:
    add_curved_panel(side);add_curved_panel(side,True)

def combine(shell,trim):
    out=copy.deepcopy(shell);offset=len(out['positions']);mapping={}
    for i,name in enumerate(trim['material_slots']):
        if name not in out['material_slots']:out['material_slots'].append(name)
        mapping[i]=out['material_slots'].index(name)
    out['positions']+=trim['positions'];out['weights']+=trim['weights'];out['triangles'] += [[i+offset for i in f] for f in trim['triangles']]
    out['triangle_materials'] += [mapping[i] for i in trim['triangle_materials']]
    for k in ['normals','uv']:out[k]+=trim[k]
    out['contract']='TS01 V7 native closed hand surface and exact cuff boundary; anatomy-local protection transfer'
    return out

canonical_out=combine(base,details);write(D/'gloves_M4_V7Master.json',canonical_out)
records=manifest['records'];report=[]
only=set(sys.argv[sys.argv.index('--rigs')+1].split(',')) if '--rigs' in sys.argv else None
for label,row in capture['rows'].items():
    if not label.startswith('Gloves_') or label in ['Gloves_Jason','Gloves_Kaitlin']:continue
    rig=label[7:];native=read(row['file'])
    if only and rig not in only:continue
    authored=read(fitted/f'{rig}.json') if (fitted/f'{rig}.json').exists() else None
    has_native=authored and 'canonical_positions' in authored
    if has_native:
        shell=native_shell(authored,native);trim=warp_gloves(details,native)
        if rig.endswith('_l') or rig.endswith('_r'):
            side=rig[-1];names=[b['name'] for b in trim['bones']];mass=np.array([sum(w for bi,w in ws if names[bi].endswith('_'+side)) for ws in trim['weights']]);trim=subset(trim,np.mean(mass[np.array(trim['triangles'])],axis=1)>.5)
        out=combine(shell,trim)
    else:out=warp_gloves(canonical_out,native)
    path=D/f'gloves_{rig}_Wear.json';write(path,out)
    records=[r for r in records if (r['kind'],r['rig'])!=('gloves',rig)]+[dict(kind='gloves',rig=rig,file=str(path),source=out['source'],slots=out['material_slots'])]
    report.append(dict(rig=rig,vertices=len(out['positions']),triangles=len(out['triangles']),native_v7_shell=bool(has_native)))
    print('TS01_V7_GLOVE',rig,len(out['positions']),flush=True);del out;gc.collect()
manifest['records']=records;write(R/'derived.json',manifest)
write(R/'QualityR3/fp-fit.json',dict(profiles=report,foundation='Accepted BarePalmV7 / FittedFieldGlovesV1',runtime_tested=False))
