"""Author a continuous rest-space garment field; no runtime/preview execution.

Discard all earlier per-vertex collision morphs. A fixed cylindrical cloth cage
drives the torso and hem, while sewn-surface weights identify the arm region.
Collision contributes only outward scalar ease to this fixed parameterization.
No changing nearest-face attachment or inverse blended skin matrices is used.
"""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009')
ROOT=BASE/'V04'; TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V01/Authoring/FacelessResearcher_V01.blend'))
rig=bpy.data.objects['root']; body=bpy.data.objects['Researcher_CompleteBody']
coat=bpy.data.objects['Researcher_LabCoat_Continuous']; pants=bpy.data.objects['Researcher_Trousers']
scene=bpy.context.scene; names=[b.name for b in rig.data.bones]; ni={n:i for i,n in enumerate(names)}
source=json.loads((ROOT/'waist_source.json').read_text(encoding='utf-8'))

def pack(o):
    p=np.array([v.co[:] for v in o.data.vertices]); w=np.zeros((len(p),len(names)),np.float64)
    gn={g.index:g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        for g in v.groups:
            if gn[g.group] in ni: w[v.index,ni[gn[g.group]]]=g.weight
    return p,w

def smooth(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1); return t*t*(3-2*t)

def normalize(w):
    # Match the eight-influence authoring contract before computing morphs.
    indices=np.argpartition(w,-8,axis=1)[:,-8:]
    limited=np.zeros_like(w); np.put_along_axis(limited,indices,np.take_along_axis(w,indices,axis=1),axis=1)
    limited[limited<1.e-6]=0
    return limited/np.maximum(limited.sum(1,keepdims=True),1.e-12)

def put(o,w):
    o.vertex_groups.clear()
    for j,n in enumerate(names):
        idx=np.flatnonzero(w[:,j]>0)
        if not len(idx): continue
        group=o.vertex_groups.new(name=n)
        for i in idx: group.add([int(i)],float(w[i,j]),'REPLACE')

def sparse(w):
    return [(j,np.flatnonzero(w[:,j]>0),w[w[:,j]>0,j,None]) for j in range(len(names)) if np.any(w[:,j]>0)]

def deform(p,s,m,vector=False):
    out=np.zeros_like(p)
    for j,ids,weight in s:
        q=p[ids]@m[j,:3,:3].T
        if not vector:q+=m[j,:3,3]
        out[ids]+=q*weight
    return out

def tree(p,t): return BVHTree.FromPolygons([Vector(v) for v in p],t.tolist(),all_triangles=True)

cp,cw=pack(coat); half=int(coat['outer_vertex_count'])
coat.shape_key_clear()
coat.data.calc_loop_triangles()
ct=np.array([tuple(t.vertices) for t in coat.data.loop_triangles if all(i<half for i in t.vertices)])
edges=np.array([tuple(e.vertices) for e in coat.data.edges if all(i<half for i in e.vertices)])
a,b=edges.T; degree=np.maximum(np.bincount(np.r_[a,b],minlength=half),1)[:,None]
active=np.flatnonzero(cw[:half].sum(0)>0); field=cw[:half,active].copy()
# Smooth across the actual sewn mesh, including the former 1.05 m weight seam.
for _ in range(64):
    sums=np.column_stack([np.bincount(a,weights=field[b,c],minlength=half)+np.bincount(b,weights=field[a,c],minlength=half) for c in range(len(active))])
    field=.45*field+.55*sums/degree
cw[:half]=0; cw[:half,active]=field
arm_ids=[ni[n] for n in names if n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','wrist'))]
arm=cw[:half,arm_ids].sum(1)
torso=(1-smooth(.025,.35,arm))*(1-smooth(1.37,1.49,cp[:half,2]))

# Stable garment coordinates, shared by the cage, mesh, placket and pockets.
NZ,NA=40,64; Z0,Z1=.74,1.48; CY=.017
zz=np.linspace(Z0,Z1,NZ); aa=np.arange(NA)*2*math.pi/NA
radial=np.stack((np.sin(aa),-np.cos(aa),np.zeros(NA)),axis=1)
directions=np.tile(radial,(NZ,1)); centers=np.column_stack((np.zeros(NZ*NA),np.full(NZ*NA,CY),np.repeat(zz,NA)))
coat_tree=tree(cp[:half],ct)
gridp=[]; gridw=[]; radii=[]
for z in zz:
    rx=float(np.interp(z,[.74,1.05,1.14,1.25,1.36,1.44,1.48],[.244,.20,.175,.156,.183,.178,.145]))
    ry=float(np.interp(z,[.74,1.05,1.20,1.35,1.45,1.48],[.17,.137,.13,.165,.141,.12]))
    center=Vector((0,CY,z))
    for d in radial:
        expected=1/math.sqrt((d[0]/rx)**2+(d[1]/ry)**2)
        hit=coat_tree.ray_cast(center,Vector(d),.35)
        if hit[0] is None or abs((hit[0]-center).length-expected)>.06:
            hit=coat_tree.find_nearest(center+Vector(d)*expected)
            radius=expected
        else:radius=(hit[0]-center).length
        tri=ct[hit[2]]
        abc=np.array(barycentric_transform(hit[0],*(Vector(cp[k]) for k in tri),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))))
        abc=np.maximum(abc,0);abc/=abc.sum()
        radii.append(radius); gridw.append(abc@cw[tri])

def neighbors(x,axis):
    if axis==1:return np.roll(x,1,axis),np.roll(x,-1,axis)
    return np.concatenate((x[:1],x[:-1]),0),np.concatenate((x[1:],x[-1:]),0)

def average_grid(x,iterations):
    for _ in range(iterations):
        for axis in [0,1]:
            lo,hi=neighbors(x,axis);x=(lo+2*x+hi)*.25
    return x

gw=average_grid(np.array(gridw).reshape(NZ,NA,-1),6).reshape(-1,len(names))
# The torso cage must never inherit arms at the sides of the shoulders.
gw[:,arm_ids]=0; gw=normalize(gw)
gr=average_grid(np.array(radii).reshape(NZ,NA),3).ravel()
gp=centers+directions*gr[:,None]

def mapping(p):
    u=np.mod(np.arctan2(p[:,0],-(p[:,1]-CY)),2*math.pi)*NA/(2*math.pi)
    v=np.clip((p[:,2]-Z0)/(Z1-Z0)*(NZ-1),0,NZ-1-1.e-8)
    iu=np.floor(u).astype(int); iv=np.floor(v).astype(int); fu=u-iu;fv=v-iv
    ids=np.column_stack((iv*NA+iu,iv*NA+(iu+1)%NA,(iv+1)*NA+iu,(iv+1)*NA+(iu+1)%NA))
    weights=np.column_stack(((1-fv)*(1-fu),(1-fv)*fu,fv*(1-fu),fv*fu))
    return ids,weights

def interpolate(values,ids,weights):
    return np.einsum('nk,nk...->n...',weights,values[ids])

ci,ca=mapping(cp[:half]); cage_weights=interpolate(gw,ci,ca)
cw[:half]=normalize(cw[:half]*(1-torso[:,None])+cage_weights*torso[:,None])
cw[half:]=cw[:half];put(coat,cw)
direction=cp[:half].copy();direction[:,1]-=CY;direction[:,2]=0
direction/=np.maximum(np.linalg.norm(direction,axis=1,keepdims=True),1.e-8)
# Add a modest sewing allowance in rest space, blended anatomically at shoulders.
padding=direction*(.008*torso[:,None])
details=[]
for o in list(scene.objects):
    if o.type!='MESH' or not o.name.startswith(('Researcher_HipPocket','Researcher_ChestPocket','Researcher_ID','Researcher_CentrePlacket','Researcher_CoatButton')):continue
    p,w=pack(o); triangles=[];coords=[]
    for v in p:
        hit=coat_tree.find_nearest(Vector(v));tri=ct[hit[2]]
        abc=np.array(barycentric_transform(hit[0],*(Vector(cp[k]) for k in tri),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))))
        abc=np.maximum(abc,0);abc/=abc.sum();triangles.append(tri);coords.append(abc)
    tri=np.array(triangles);abc=np.array(coords)
    p+=interpolate(padding,tri,abc);w=normalize(interpolate(cw[:half],tri,abc));put(o,w)
    details.append((o,p,tri,abc))
cp+=np.vstack((padding,padding))
for o,p in [(coat,cp)]+[(d[0],d[1]) for d in details]:
    o.shape_key_clear();o.data.vertices.foreach_set('co',p.astype(np.float32).ravel());o.data.update();o.shape_key_add(name='Basis')

# Independent low-resolution production colliders. The authored/rendered body
# and trousers remain complete and unchanged. Exclude arms by bone influence.
colliders=[]
for source_mesh in [body,pants]:
    temp=source_mesh.copy();temp.data=source_mesh.data.copy();bpy.context.collection.objects.link(temp)
    temp.hide_set(False);temp.modifiers.clear();temp.shape_key_clear()
    bpy.context.view_layer.objects.active=temp
    bpy.ops.object.select_all(action='DESELECT');temp.select_set(True)
    count=sum(len(p.vertices)-2 for p in temp.data.polygons)
    mod=temp.modifiers.new('AuthoringCollisionProxy','DECIMATE');mod.ratio=min(1.,14000/max(1,count))
    bpy.ops.object.modifier_apply(modifier=mod.name)
    p,w=pack(temp);temp.data.calc_loop_triangles();t=np.array([tuple(f.vertices) for f in temp.data.loop_triangles])
    if source_mesh==body:
        excluded=w[:,arm_ids].sum(1)>.25
        excluded|=w[:,[ni[n] for n in names if n.startswith(('head','neck'))]].sum(1)>.5
        t=t[~excluded[t].any(1)]
    colliders.append((p,sparse(w),t));bpy.data.objects.remove(temp,do_unlink=True)
offset=len(colliders[0][0]);collision_triangles=np.vstack((colliders[0][2],colliders[1][2]+offset))
collision_rest=np.vstack([p for p,s,t in colliders])
triangle_z=collision_rest[collision_triangles,2]
# Fixed anatomical bands prevent a bent torso's rays from reaching another
# body region (for example the knee in front of the chest). Registration is
# defined once in rest space, never reassigned according to the current pose.
bands=[]
for ring in range(0,NZ,4):
    end=min(ring+4,NZ)
    included=(triangle_z.min(1)<zz[end-1]+.065)&(triangle_z.max(1)>zz[ring]-.065)
    bands.append((range(ring*NA,end*NA),collision_triangles[included]))
gs=sparse(gw);curves={};manifest={}

for role,entry in source['clips'].items():
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=entry['file'],use_anim=True)
    imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
    first,last=map(int,donor.animation_data.action.frame_range);fps=scene.render.fps/scene.render.fps_base
    frames=min(last-first+1,round(entry['duration']*fps)+1)
    step=10 if role=='idle' else 1 if role=='hit' else 3
    samples=sorted(set(range(0,frames,step))|{frames-1});values=[]
    inv={n:(donor.matrix_world@donor.data.bones[n].matrix_local).inverted() for n in names}
    for frame in samples:
        scene.frame_set(first+frame);bpy.context.view_layer.update()
        mats=np.array([np.array(donor.matrix_world@donor.pose.bones[n].matrix@inv[n]) for n in names])
        positions=np.vstack([deform(p,s,mats) for p,s,t in colliders])
        posed=deform(gp,gs,mats);outward=deform(directions,gs,mats,True)
        length=np.linalg.norm(outward,axis=1);unit=outward/np.maximum(length[:,None],1.e-8)
        ease=np.zeros(NZ*NA)
        for indices,triangles in bands:
            collision=tree(positions,triangles)
            for i in indices:
                p,d=posed[i],unit[i]
                # Local garment contact only; a distant opposing folded region
                # must not inflate the garment toward it.
                reach=.10*length[i]
                h,_,_,_=collision.ray_cast(Vector(p+d*reach),Vector(-d),reach+gr[i]*length[i])
                if h is not None:ease[i]=max(0.,(np.dot(np.array(h)-p,d)+.021)/max(length[i],.4))
        # Broad spatial support gives an envelope instead of isolated point pushes.
        ease=ease.reshape(NZ,NA)
        for _ in range(3):
            for axis in [0,1]:
                lo,hi=neighbors(ease,axis);ease=np.maximum(ease,np.maximum(lo,hi))
        ease=average_grid(ease,6)
        values.append(ease)
        print('RESEARCHER_STABLE_CAGE',role,frame,'ease_m',round(float(ease.max()),5),flush=True)
    values=np.array(values)
    # Dilation followed by a positive temporal filter prevents contact switching
    # from producing one-frame shrink/pop. Loop endpoints share the same field.
    looping=role in ['idle','walk'];filtered=values.copy()
    def timeshift(x,k):
        if looping:return np.roll(x,k,axis=0)
        return x[np.clip(np.arange(len(x))-k,0,len(x)-1)]
    for k in [-1,1]:filtered=np.maximum(filtered,timeshift(values,k))
    filtered=(timeshift(filtered,-2)+4*timeshift(filtered,-1)+6*filtered+4*timeshift(filtered,1)+timeshift(filtered,2))/16
    if looping:filtered[0]=filtered[-1]=(filtered[0]+filtered[-1])*.5
    keys=['FRS4_'+role+'_%03d'%f for f in samples]
    curves[role]={key:[float(np.interp(f,samples,[1. if s==sample else 0. for s in samples])) for f in range(frames)] for key,sample in zip(keys,samples)}
    manifest[role]={'frames':frames,'fps':fps,'samples':samples,'source':entry['source'],'duration':entry['duration'],
        'maximum_cage_ease_m':float(filtered.max()),'method':'fixed garment coordinates; scalar radial ease; spatial and temporal smoothing'}
    for key,value in zip(keys,filtered):
        ease=interpolate(value.ravel(),ci,ca)
        corr=direction*(ease*torso)[:,None]
        shape=coat.shape_key_add(name=key);shape.data.foreach_set('co',(cp+np.vstack((corr,corr))).astype(np.float32).ravel())
        for o,p,tri,abc in details:
            dc=interpolate(corr,tri,abc)
            shape=o.shape_key_add(name=key);shape.data.foreach_set('co',(p+dc).astype(np.float32).ravel())
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for o in [coat]+[d[0] for d in details]:
    for key in o.data.shape_keys.key_blocks:key.value=0
scene.frame_set(0);bpy.context.view_layer.update()
(ROOT/'stable_curves.json').write_text(json.dumps(curves),encoding='utf-8')
(ROOT/'stable_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V04.blend'))
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessReceptionist/export_v04.py').read_text(encoding='utf-8').replace('FacelessReceptionist20261007','FacelessResearcher20261009').replace('FacelessReceptionist','FacelessResearcher').replace('Receptionist','Researcher')
exec(compile(export,'researcher_v04_export','exec'))
