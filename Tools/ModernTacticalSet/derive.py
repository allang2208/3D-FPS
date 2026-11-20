"""Build native body/weapon derivatives from the saved TS01 master payloads."""
import json,copy,sys,gc
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/Integration';D=R/'Delivery';I=R/'Inputs'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
prepared=read(R/'prepared.json');capture=read(R/'captured.json');config=read(I/'modular_outfits.json');bodyconfig=read(I/'player_body.json')
if not prepared['completed'] or not capture['completed']:raise RuntimeError('Complete the author and native-input stages first')
selected=set(sys.argv[sys.argv.index('--parts')+1].split(',')) if '--parts' in sys.argv else None
records=read(R/'derived.json')['records'] if selected else []
def record(kind,rig,d):
    global records
    if kind in ('pants','pants_boot','pants_short','pants_high'):
        from cuff_topology import separate_shared_edges
        d=copy.deepcopy(d);separate_shared_edges(d)
    file=D/(kind+'_'+rig+'_Wear.json');write(file,d);records=[r for r in records if (r['kind'],r['rig'])!=(kind,rig)];records.append(dict(kind=kind,rig=rig,file=str(file),source=d['source'],slots=d['material_slots']));print('TS01_NATIVE_DERIVED',kind,rig,flush=True)
def transport_normals(d, original):
    faces=np.asarray(d['triangles'])
    def frames(points):
        tri=np.asarray(points)[faces];edge=tri[:,1]-tri[:,0]
        normal=np.cross(edge,tri[:,2]-tri[:,0])
        length=np.linalg.norm(normal,axis=1,keepdims=True)
        normal/=np.maximum(length,1e-12)
        edge/=np.maximum(np.linalg.norm(edge,axis=1,keepdims=True),1e-12)
        return np.stack([edge,np.cross(normal,edge),normal],axis=1),length[:,0]>1e-10
    old,ok=frames(original);new,valid=frames(d['positions'])
    n=np.asarray(d['normals'])
    rotation=old.transpose(0,2,1)@new
    n[ok&valid]=n[ok&valid]@rotation[ok&valid]
    n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12)
    d['normals']=n.tolist()
def remap_bones(d,target):
    names={b['name']:b['index'] for b in target['bones']};old=d['bones'];mapping={b['index']:names[b['name']] for b in old if b['name'] in names}
    d['weights']=[[[mapping[bi],w] for bi,w in row] for row in d['weights']];d['bones']=target['bones'];d['source']=target['source']
def subset(d,mask):
    f=np.array(d['triangles'])[mask];used=np.unique(f);mapping=np.full(len(d['positions']),-1,int);mapping[used]=np.arange(len(used));indices=np.flatnonzero(mask)
    out=copy.deepcopy({k:v for k,v in d.items() if k not in ['positions','triangles','normals','uv','weights','triangle_materials']})
    out['positions']=[d['positions'][int(i)] for i in used];out['weights']=[d['weights'][int(i)] for i in used];out['triangles']=mapping[f].tolist()
    for k in ['normals','uv','triangle_materials']:out[k]=[d[k][int(i)] for i in indices]
    return out
def append(dst,src,mask):
    patch=subset(src,mask);names={b['name']:b['index'] for b in dst['bones']};bone_map={b['index']:names[b['name']] for b in patch['bones']}
    matmap={}
    for i in sorted(set(patch['triangle_materials'])):
        matmap[i]=len(dst['material_slots']);dst['material_slots'].append('NATIVE:'+patch['materials'][i])
    base=len(dst['positions']);dst['positions'].extend(patch['positions']);dst['weights'].extend([[[bone_map[bi],w] for bi,w in ws] for ws in patch['weights']]);dst['triangles'].extend([[base+v for v in f] for f in patch['triangles']]);dst['uv'].extend(patch['uv']);dst['normals'].extend(patch['normals']);dst['triangle_materials'].extend([matmap[m] for m in patch['triangle_materials']])

# Current lower-body wrappers include native skin areas above the cloth/boot cut.
# Retain those exact patches rather than hiding an entire waist or lower leg.
def old_skin_patch(kind):
    file=P/'SourceAssets/ST6LowerSet20261018'/('Jason_ST6Boots.json' if kind=='boots' else 'Jason_ST6Trousers.json')
    d=read(file);d['material_slots']=['unused']*7;d['materials']=['']*6+['/Game/AsianMale_Jason/Material/MI_Body_Baked.MI_Body_Baked']
    return d,np.array(d['triangle_materials'])==6

male={}
for row in prepared['rows']:
    if selected and row['kind'] not in selected:continue
    kind=row['kind'];d=read(row['file']);d['materials']=d['material_slots'];native=read(I/'Body_Jason.json');remap_bones(d,native)
    if kind in ['pants','pants_boot','boots']:
        skin,mask=old_skin_patch('boots' if kind=='boots' else 'pants');append(d,skin,mask)
    male[kind]=d
    if kind!='helmet':record(kind,'Jason',d)

# Preserve the current production trouser cuffs for short and high footwear.
# The new detail geometry shares the ST6 garment surface; only lower-leg deltas
# are transferred, so its authored pockets, knee panels and waistband stay intact.
from scipy.spatial import cKDTree
if 'pants' in male:
    old_base=read(P/'SourceAssets/ST6LowerSet20261018/Jason_ST6Trousers_Garment.json')
    base_points=np.array(old_base['positions']);tree=cKDTree(base_points)
for kind,suffix in ([('pants_short','ShortBootsFit'),('pants_high','HighBootsFit')] if 'pants' in male else []):
    out=copy.deepcopy(male['pants']);old_fit=read(P/'SourceAssets/ST6LowerSet20261018'/('Jason_ST6Trousers_'+suffix+'.json'))
    delta=np.array(old_fit['positions'][:len(base_points)])-base_points
    points=np.array(out['positions']);distance,nearest=tree.query(points);mask=(points[:,2]<46)&(distance<2.)
    points[mask]+=delta[nearest[mask]];out['positions']=points.tolist();transport_normals(out,male['pants']['positions']);male[kind]=out;record(kind,'Jason',out)

# Established measured Jason-to-Kaitlin surface field and native skeleton.
sys.path.insert(0,str(P/'Tools/KaitlinPlayer'));from body_surface_fit import BodySurfaceFit,bind_warp,neighbors
W=P/'SourceAssets/KaitlinPlayer20261023';captured=read(W/'FitInputs/captured.json');oldconfig=read(W/'FitInputs/modular_outfits.json');oldbody=read(W/'FitInputs/player_body.json')
source=read(W/'FitInputs'/captured[oldconfig['profiles'][oldbody['body_mesh']]['native_bare_skin']]['file']);target=read(W/'NativeGeometry/MHC_Kaitlin_Body.json')
fit=BodySurfaceFit(source,target,read(W/'body_correspondence.json')['target_to_source_vertices']);female_native=read(I/'Body_Kaitlin.json')
def fit_inner_seam(d,result):
    # Blend the three anatomical fit fields across a welded seam. Selecting
    # only its dominant region would step between fields on adjacent vertices.
    p=np.asarray(d['positions']);x,y,z=p.T
    def ease(a,b,v):
        t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
    amount=(1-ease(3,12,abs(x)))*ease(61,68,z)*(1-ease(82,90,z))
    idx=np.flatnonzero(amount>0)
    subset={'bones':d['bones'],'positions':p[idx],'weights':[d['weights'][i] for i in idx]}
    moved=bind_warp(subset,fit.target);residual=np.zeros_like(moved);names=[b['name'] for b in d['bones']]
    mass=np.zeros((len(idx),3))
    for j,ws in enumerate(subset['weights']):
        for bi,w in ws:
            name=names[bi];r=1 if name.startswith('thigh') and name.endswith('_l') else 2 if name.startswith('thigh') and name.endswith('_r') else 0
            mass[j,r]+=w
    for k,region in enumerate(['torso','thigh_l','thigh_r']):
        near,weights=neighbors(moved,np.full(len(moved),region),fit.points,fit.regions)
        residual+=mass[:,k,None]*(fit.residual[near]*weights[:,:,None]).sum(axis=1)
    old=np.asarray(result['positions']);old[idx]+=(moved+residual-old[idx])*amount[idx,None]
    result['positions']=old.tolist()

for kind,d in male.items():
    if kind=='helmet':continue
    out=copy.deepcopy(d);result=fit.garment(d)
    if kind=='vest':
        from smooth_vest_frame import positions as vest_positions
        result['positions']=vest_positions(d,target['bones'])
    if kind=='boots':
        from smooth_boot_frame import positions as boot_positions
        moved=np.array(boot_positions(d,target['bones']));old_result=np.array(result['positions'])
        skin_slots=[i for i,s in enumerate(d['material_slots']) if s.startswith('NATIVE:')]
        skin_vertices=np.unique(np.asarray(d['triangles'])[np.isin(d['triangle_materials'],skin_slots)])
        moved[skin_vertices]=old_result[skin_vertices];result['positions']=moved.tolist()
    if kind.startswith('pants'):fit_inner_seam(d,result)
    out['positions']=result['positions'];out['weights']=result['weights'];out['bones']=target['bones'];remap_bones(out,female_native)
    # Actual female native body material path comes from its captured material array.
    native_skin=next((x for x in female_native['materials'] if x and ('Body' in x or 'body' in x)),None)
    if any(x.startswith('NATIVE:') for x in out['material_slots']) and not native_skin:raise RuntimeError('Female native body material unavailable')
    if native_skin:out['material_slots']=[('NATIVE:'+native_skin) if x.startswith('NATIVE:') else x for x in out['material_slots']]
    transport_normals(out,d['positions']);record(kind,'Kaitlin',out);del out;gc.collect()

# Native first-person meshes use their own reference bone positions and axes.
# Normalise component scale separately from orientation to avoid 100x FBX rigs.
def warp_gloves(d,native):
    out=copy.deepcopy(d);dst={b['name']:b for b in native['bones']};source=d['bones'];maps=[]
    required={bi for ws in d['weights'] for bi,w in ws if w>0}
    for bone in source:
        if bone['index'] not in required:maps.append(None);continue
        b=bone
        while b['name'] not in dst and b['parent']>=0:b=source[b['parent']]
        if b['name'] not in dst:raise RuntimeError('Cannot map '+bone['name'])
        t=dst[b['name']];sa=np.array(b['axes']);ta=np.array(t['axes']);sa/=np.linalg.norm(sa,axis=1)[:,None];ta/=np.linalg.norm(ta,axis=1)[:,None]
        maps.append((b,t,np.linalg.inv(sa)@ta))
    p=np.array(d['positions']);new=np.zeros_like(p);jac=np.zeros((len(p),3,3));weights=[];bybone=[[] for _ in source]
    for vi,ws in enumerate(d['weights']):
        merged={}
        for bi,w in ws:bybone[bi].append((vi,w));ti=maps[bi][1]['index'];merged[ti]=merged.get(ti,0)+w
        weights.append(list(merged.items()))
    for bi,rows in enumerate(bybone):
        if not rows:continue
        ids=np.array([v for v,w in rows]);w=np.array([w for v,w in rows]);b,t,rot=maps[bi];new[ids]+=((p[ids]-b['position'])@rot+t['position'])*w[:,None];jac[ids]+=rot*w[:,None,None]
    out['positions']=new.tolist();out['weights']=weights;out['bones']=native['bones'];out['source']=native['source']
    f=np.array(d['triangles']);n=np.einsum('fcj,fcjk->fck',np.array(d['normals']),jac[f]);n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12);out['normals']=n.tolist()
    return out
for label,row in capture['rows'].items():
    if 'gloves' not in male:continue
    if not label.startswith('Gloves_'):continue
    rig=label[7:]
    if rig in ['Jason','Kaitlin']:continue
    native=read(row['file']);d=warp_gloves(male['gloves'],native)
    if rig.endswith('_l') or rig.endswith('_r'):
        suffix=rig[-1];names=[b['name'] for b in d['bones']];mass=np.array([sum(w for bi,w in ws if names[bi].endswith('_'+suffix)) for ws in d['weights']]);d=subset(d,np.mean(mass[np.array(d['triangles'])],axis=1)>.5)
    record('gloves',rig,d);del d;gc.collect()

# Rigid helmet geometry is stored directly in each actual head bone's local frame.
for rig,native in ([('Jason',read(I/'Body_Jason.json')),('Kaitlin',female_native)] if 'helmet' in male else []):
    d=copy.deepcopy(male['helmet']);source_head=next(b for b in d['bones'] if b['name']=='head');target_head=next(b for b in native['bones'] if b['name']=='head')
    p=np.array(d['positions']);source_axes=np.array(source_head['axes']);local=(p-source_head['position'])@np.linalg.inv(source_axes)
    if rig=='Kaitlin':
        # Head-specific dimensional change from the two actual face sources.
        male_head=read(P/'SourceAssets/JasonPlayer20261003/head_geometry.json');female_head=read(W/'NativeGeometry/SKM_Face.json');mp=np.array(male_head['positions']);fp=np.array(female_head['positions'])
        span_m=np.percentile(mp,99,axis=0)-np.percentile(mp,1,axis=0);span_f=np.percentile(fp,99,axis=0)-np.percentile(fp,1,axis=0)
        scale=float(np.clip(np.median(span_f/span_m),.90,1.06));local*=scale
    else:scale=1.
    d['positions']=local.tolist();inv=np.linalg.inv(source_axes);n=np.array(d['normals'])@inv;n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12);d['normals']=n.tolist();d['bones']=native['bones'];d['source']=native['source'];d['weights']=[[[target_head['index'],1.]] for _ in local];d['attachment_scale']=scale
    record('helmet',rig,d)
write(R/'derived.json',dict(completed=True,records=records,source=prepared,waist_basis='Existing ST6 native waistband and skin patch; new details are below waist',runtime_tested=False))
