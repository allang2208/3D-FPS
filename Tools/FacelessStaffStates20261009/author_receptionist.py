"""M-04 V05: keep accepted V04 surfaces and add anatomical special-state cloth."""
import bpy,json,math,ast
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V05')
BASE=ROOT.parent/'V04';SHARED=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessStaffStates20261009')
for d in ['Authoring','Delivery','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/FacelessReceptionist_V04.blend'))
s=bpy.context.scene;rig=bpy.data.objects['root'];body=bpy.data.objects['Receptionist_CompleteBody']
rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
s.frame_set(0)
names=[b.name for b in rig.data.bones];index={n:i for i,n in enumerate(names)}
module=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/FacelessReceptionist/author_v04.py').read_text(encoding='utf-8'))
needed={'pts','skin','compact','deform','smooth','attachment'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in needed],type_ignores=[]),'receptionist_existing_cloth_helpers','exec'))
bp=pts(body);bw=skin(body);bc=compact(bw)
body.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in body.data.loop_triangles])
bvh=BVHTree.FromPolygons([Vector(p) for p in bp],tri,all_triangles=True)
garments={}
for o in s.objects:
    if o.type!='MESH' or not o.data.shape_keys or not any(k.name.startswith('FR4_') for k in o.data.shape_keys.key_blocks):continue
    p=pts(o);w=skin(o);kind='skirt' if o.name.startswith('Receptionist_Skirt') or 'VentFinish' in o.name else 'upper'
    data={'object':o,'points':p,'weights':w,'packed':compact(w),'kind':kind}
    if kind=='upper':
        attached=[attachment(v) for v in p]
        data['ids']=np.array([a[0] for a in attached]);data['bary']=np.array([a[1] for a in attached])
        data['offset']=p-np.array([a[2] for a in attached]);data['wrap_weights']=(bw[data['ids']]*data['bary'][:,:,None]).sum(axis=1)
        data['fade']=smooth(1.26,1.38,p[:,2])
    garments[o.name]=data
    for key in o.data.shape_keys.key_blocks:key.value=0
# Anatomical bands retain their original vertex membership while the character lies down.
# Unlike the V04 standing cage, the cross-sections never use world Z to find the legs.
zlevels=np.linspace(.455,1.145,40);na=64;angles=np.arange(na)*2*math.pi/na
radial=np.stack([np.sin(angles),-np.cos(angles)],axis=1)
armids=[index[n] for n in names if n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','wrist'))]
legmask=(abs(bp[:,0])<.36)&(bw[:,armids].sum(axis=1)<.15)
legids=[np.where((abs(bp[:,2]-z)<.025)&legmask)[0] for z in zlevels]
for i,ids in enumerate(legids):
    if len(ids)<8:legids[i]=np.where(legmask)[0][np.argsort(abs(bp[legmask,2]-zlevels[i]))[:64]]

def normalize(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-8)
def cage(posed,m):
    centers=np.array([posed[ids].mean(axis=0) for ids in legids])
    tangent=normalize(np.gradient(centers,axis=0));px=m[index['pelvis'],:3,:3]@np.array([1.,0,0])
    axesx=normalize(px[None,:]-tangent*(tangent@px)[:,None]);axesy=normalize(np.cross(tangent,axesx))
    radii=[]
    dots=radial@radial.T
    for i,ids in enumerate(legids):
        d=posed[ids]-centers[i];local=np.column_stack((d@axesx[i],d@axesy[i]))
        offset=(local.min(0)+local.max(0))*.5;centers[i]+=axesx[i]*offset[0]+axesy[i]*offset[1];local-=offset
        support=np.maximum((local@radial.T).max(0)+.025,.075)
        r=np.min(np.where(dots>.02,support[None,:]/np.maximum(dots,.02),100),axis=1)
        for _ in range(4):r=(2*r+np.roll(r,1)+np.roll(r,-1))/4
        radii.append(r)
    radii=np.array(radii)
    for _ in range(4):
        centers[1:-1]=centers[1:-1]*.5+(centers[:-2]+centers[2:])*.25
        radii[1:-1]=np.maximum(radii[1:-1],radii[1:-1]*.5+(radii[:-2]+radii[2:])*.25)
    return centers,axesx,axesy,radii

def skirt_target(p,current,sections):
    centers,x,y,r=sections
    f=np.clip((p[:,2]-zlevels[0])/(zlevels[-1]-zlevels[0])*(len(zlevels)-1),0,len(zlevels)-1-1e-6)
    lo=f.astype(int);hi=lo+1;t=(f-lo)[:,None]
    angle=np.mod(np.arctan2(p[:,0],-(p[:,1]-.027)),2*math.pi);af=angle/(2*math.pi)*na;ai=af.astype(int)%na;aj=(ai+1)%na;at=af-np.floor(af)
    radius=(r[lo,ai]*(1-at)+r[lo,aj]*at)*(1-t[:,0])+(r[hi,ai]*(1-at)+r[hi,aj]*at)*t[:,0]
    radius=np.maximum(radius,np.hypot(p[:,0],p[:,1]-.027)*.92)
    cx=normalize(x[lo]*(1-t)+x[hi]*t);cy=normalize(y[lo]*(1-t)+y[hi]*t)
    target=centers[lo]*(1-t)+centers[hi]*t+radius[:,None]*(cx*np.sin(angle)[:,None]-cy*np.cos(angle)[:,None])
    fade=smooth(1.115,1.025,p[:,2])[:,None]
    return current*(1-fade)+target*fade

def invert_skin(linear,delta):
    result=np.empty_like(delta);safe=abs(np.linalg.det(linear))>.15
    result[safe]=np.linalg.solve(linear[safe],delta[safe,:,None])[:,:,0]
    if not safe.all():
        uu,ss,vh=np.linalg.svd(linear[~safe]);inv=np.einsum('nij,nj,njk->nik',vh.transpose(0,2,1),1/np.maximum(ss,.35),uu.transpose(0,2,1))
        result[~safe]=np.einsum('nij,nj->ni',inv,delta[~safe])
    return result
source=json.loads((SHARED/'source.json').read_text(encoding='utf-8'));curves={};manifest={}
for role,entry in source['clips'].items():
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=entry['file'],use_anim=True)
    imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
    first=int(donor.animation_data.action.frame_range[0]);fps=s.render.fps/s.render.fps_base
    frames=round(entry['duration']*fps)+1;samples=sorted(set(range(0,frames,max(1,round(fps/15))))|{frames-1})
    inverse={n:(donor.matrix_world@donor.data.bones[n].matrix_local).inverted() for n in names}
    corrections={n:[] for n in garments}
    for frame in samples:
        s.frame_set(first+frame);bpy.context.view_layer.update()
        m=np.array([np.array(donor.matrix_world@donor.pose.bones[n].matrix@inverse[n]) for n in names]);posed=deform(bp,bc,m);sections=cage(posed,m)
        for name,data in garments.items():
            p=data['points'];w=data['weights'];current=deform(p,data['packed'],m)
            if data['kind']=='skirt':
                target=skirt_target(p,current,sections)
                if name in ['Receptionist_Skirt','Receptionist_Skirt_BackVentUnderlap','Receptionist_Skirt_Waistband']:
                    half=len(p)//2;target[half:]=target[:half]+current[half:]-current[:half]
            else:
                ids=data['ids'];abc=data['bary'];hit=(posed[ids]*abc[:,:,None]).sum(1)
                wrap=np.einsum('nb,bij->nij',data['wrap_weights'],m[:,:3,:3]);offset=np.einsum('nij,nj->ni',wrap,data['offset'])
                normal=normalize(np.cross(posed[ids[:,1]]-posed[ids[:,0]],posed[ids[:,2]]-posed[ids[:,0]]))
                distance=np.sum(offset*normal,axis=1);ease=.016 if name=='Receptionist_Blazer_Continuous' else .006 if name=='Receptionist_Shirt_Continuous' else .019
                offset+=normal*np.minimum(.008,np.maximum(0,ease-distance))[:,None]
                target=current+(hit+offset-current)*data['fade'][:,None]
            linear=np.einsum('nb,bij->nij',w,m[:,:3,:3]);corrections[name].append(invert_skin(linear,target-current))
        print('M04_V05_CLOTH',role,frame,flush=True)
    keys=['FR5_'+role+'_%03d'%f for f in samples]
    curves[role]={key:[float(np.interp(f,samples,[1. if s==sample else 0. for s in samples])) for f in range(frames)] for key,sample in zip(keys,samples)}
    manifest[role]={'fps':fps,'frames':frames,'samples':samples,'duration':entry['duration'],'source':entry['source']}
    for name,data in garments.items():
        o=data['object'];p=data['points'];c=np.array(corrections[name]);filtered=c.copy()
        if len(c)>2:filtered[1:-1]=c[1:-1]*.5+(c[:-2]+c[2:])*.25
        if role=='dizzy':filtered[0]=filtered[-1]=(filtered[0]+filtered[-1])*.5
        if role=='hit' and 'FR4_idle_000' in o.data.shape_keys.key_blocks:
            old=np.empty(p.size,np.float64);o.data.shape_keys.key_blocks['FR4_idle_000'].data.foreach_get('co',old)
            old=old.reshape(p.shape)-p
            filtered[0]=filtered[-1]=old
            if len(filtered)>3:filtered[1]=filtered[1]*.7+old*.3;filtered[-2]=filtered[-2]*.7+old*.3
        for key,delta in zip(keys,filtered):
            shape=o.shape_key_add(name=key);shape.data.foreach_set('co',(p+delta).astype(np.float32).ravel())
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for data in garments.values():
    for key in data['object'].data.shape_keys.key_blocks:key.value=0
s.frame_set(0)
(ROOT/'state_curves.json').write_text(json.dumps(curves),encoding='utf-8');(ROOT/'state_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V05.blend'))
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessReceptionist/export_v04.py').read_text(encoding='utf-8').replace('V04','V05')
exec(compile(export,'receptionist_v05_export','exec'))
print('M04_V05_STATES_EXPORTED',flush=True)