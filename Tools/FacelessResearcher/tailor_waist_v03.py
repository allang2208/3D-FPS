"""Rebuild circumferential waist contact for the four current researcher clips."""
import bpy,bmesh,json
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009')
ROOT=BASE/'V03';TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V02/Authoring/FacelessResearcher_V02.blend'))
rig=bpy.data.objects['root'];body=bpy.data.objects['Researcher_CompleteBody']
coat=bpy.data.objects['Researcher_LabCoat_Continuous'];pants=bpy.data.objects['Researcher_Trousers']
scene=bpy.context.scene;names=[b.name for b in rig.data.bones];ni={n:i for i,n in enumerate(names)}
source=json.loads((ROOT/'waist_source.json').read_text(encoding='utf-8'))
oldcurves=json.loads((BASE/'V01/corrective_curves.json').read_text(encoding='utf-8'))
oldcurves.update(json.loads((BASE/'V02/reaction_curves.json').read_text(encoding='utf-8')))

def pack(o):
    p=np.array([v.co[:] for v in o.data.vertices]);w=np.zeros((len(p),len(names)),np.float32)
    gn={g.index:g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        for g in v.groups:
            if gn[g.group] in ni:w[v.index,ni[gn[g.group]]]=g.weight
    return p,w

def deform(p,w,m):
    linear=np.einsum('nb,bij->nij',w,m[:,:3,:3])
    return np.einsum('nij,nj->ni',linear,p)+w@m[:,:3,3],linear

def tree(p,t):return BVHTree.FromPolygons([Vector(v) for v in p],t.tolist(),all_triangles=True)

def smooth(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)

def project(p,indices,collision,clearance):
    for i in indices:
        h,n,_,_=collision.find_nearest(Vector(p[i]))
        signed=(Vector(p[i])-h).dot(n)
        if signed<clearance:p[i]+=np.array(n)*(clearance-signed)

bp,bw=pack(body);oldcp,cw=pack(coat);pp,pw=pack(pants)
half=int(coat['outer_vertex_count']);phalf=len(pp)//2
body.data.calc_loop_triangles();bt=np.array([tuple(f.vertices) for f in body.data.loop_triangles])
coat.data.calc_loop_triangles();ct=np.array([tuple(f.vertices) for f in coat.data.loop_triangles if all(i<half for i in f.vertices)])
pants.data.calc_loop_triangles()
pt=[tuple(f.vertices) for f in pants.data.loop_triangles if all(i<phalf for i in f.vertices)]
# Close the trouser collider at its existing openings. Otherwise a nearest
# normal above the waistband treats an open side wall as an infinite plane.
bm=bmesh.new();verts=[bm.verts.new(Vector(v)) for v in pp[:phalf]]
for tri in pt:bm.faces.new([verts[i] for i in tri])
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.index_update()
pt=np.array([tuple(v.index for v in f.verts) for f in bm.faces]);bm.free()
body_tree=tree(bp,bt);pants_tree=tree(pp,pt);coat_tree=tree(oldcp[:half],ct)
zone=np.flatnonzero((oldcp[:half,2]<1.30)&(np.abs(oldcp[:half,0])<.34))
edges=np.array([tuple(e.vertices) for e in coat.data.edges if all(i<half for i in e.vertices)])
a,b=edges.T;degree=np.maximum(np.bincount(np.r_[a,b],minlength=half),1)[:,None]

def diffuse(delta):
    sums=np.column_stack([np.bincount(a,weights=delta[b,c],minlength=half)+np.bincount(b,weights=delta[a,c],minlength=half) for c in range(3)])
    return .55*delta+.45*sums/degree

# Preserve the old upper-body deformation. Only the lower coat and a broad,
# smooth waist overlap are rebuilt; no body triangles or trousers are hidden.
oldshape={}
for key in coat.data.shape_keys.key_blocks:
    if key.name=='Basis':continue
    co=np.empty(oldcp.size,np.float32);key.data.foreach_get('co',co)
    oldshape[key.name]=co.reshape(oldcp.shape)-oldcp

cp=oldcp.copy();base=cp[:half].copy()
for _ in range(6):
    base=oldcp[:half]+diffuse(base-oldcp[:half])
    project(base,zone,body_tree,.010)
    project(base,zone,pants_tree,.020)
padding=base-oldcp[:half];cp+=np.vstack((padding,padding))

details=[]
for o in scene.objects:
    if o.type!='MESH' or not o.name.startswith(('Researcher_HipPocket','Researcher_ChestPocket','Researcher_ID','Researcher_CentrePlacket','Researcher_CoatButton')):continue
    p,w=pack(o);triangles=[];coords=[]
    for v in p:
        hit=coat_tree.find_nearest(Vector(v));tri=ct[hit[2]]
        abc=np.array(barycentric_transform(hit[0],*(Vector(oldcp[k]) for k in tri),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))))
        abc=np.maximum(abc,0);abc/=abc.sum();triangles.append(tri);coords.append(abc)
    tri=np.array(triangles);abc=np.array(coords)
    p+=np.einsum('nk,nkj->nj',abc,padding[tri])
    details.append((o,p,w,tri,abc))
for o,p in [(coat,cp)]+[(d[0],d[1]) for d in details]:
    o.shape_key_clear();o.data.vertices.foreach_set('co',p.astype(np.float32).ravel());o.data.update();o.shape_key_add(name='Basis')

# Register the whole transition band, with no branch at the old 1.05 m waist.
ids=[];bary=[];offset=[];wrapweights=[]
for i in zone:
    hit=body_tree.find_nearest(Vector(cp[i]));tri=bt[hit[2]]
    abc=np.array(barycentric_transform(hit[0],*(Vector(bp[k]) for k in tri),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))))
    abc=np.maximum(abc,0);abc/=abc.sum()
    ids.append(tri);bary.append(abc);offset.append(cp[i]-np.array(hit[0]));wrapweights.append(abc@bw[tri])
ids=np.array(ids);bary=np.array(bary);offset=np.array(offset);wrapweights=np.array(wrapweights)
wrap=smooth(.93,1.22,cp[zone,2])[:,None]
zoneblend=(1-smooth(1.20,1.30,cp[zone,2]))[:,None]
curves={};manifest={}

for role,entry in source['clips'].items():
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=entry['file'],use_anim=True)
    imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
    first,last=map(int,donor.animation_data.action.frame_range);fps=scene.render.fps/scene.render.fps_base
    frames=min(last-first+1,round(entry['duration']*fps)+1)
    step=10 if role=='idle' else 1 if role=='hit' else 3
    samples=sorted(set(list(range(0,frames,step))+[frames-1]))
    keys=['FRS3_'+role+'_%03d'%f for f in samples]
    curves[role]={key:[float(np.interp(f,samples,[1. if s==sample else 0. for s in samples])) for f in range(frames)] for key,sample in zip(keys,samples)}
    inv={n:(donor.matrix_world@donor.data.bones[n].matrix_local).inverted() for n in names}
    manifest[role]={'frames':frames,'fps':fps,'samples':samples,'source':entry['source'],'duration':entry['duration']}
    for frame,key in zip(samples,keys):
        scene.frame_set(first+frame);bpy.context.view_layer.update()
        mats=np.array([np.array(donor.matrix_world@donor.pose.bones[n].matrix@inv[n]) for n in names])
        posed,_=deform(bp,bw,mats);posedpants,_=deform(pp,pw,mats)
        current,linear=deform(cp,cw,mats)
        oldcorr=np.zeros(oldcp.shape)
        for name,values in oldcurves[role].items():
            oldframe=min(frame/fps/entry['duration'],1.)*(len(values)-1)
            weight=float(np.interp(oldframe,np.arange(len(values)),values))
            if weight:oldcorr+=oldshape[name]*weight
        target=deform(oldcp+oldcorr,cw,mats)[0][:half]
        rotation=np.einsum('nb,bij->nij',wrapweights,mats[:,:3,:3])
        registered=np.einsum('nk,nkj->nj',bary,posed[ids])+np.einsum('nij,nj->ni',rotation,offset)
        sewn=current[zone]*(1-wrap)+registered*wrap
        target[zone]=target[zone]*(1-zoneblend)+sewn*zoneblend
        initial=target.copy();body_collision=tree(posed,bt);pants_collision=tree(posedpants,pt)
        for _ in range(8):
            target=initial+diffuse(target-initial)
            project(target,zone,body_collision,.010)
            # This is the final constraint, after body attachment and smoothing.
            project(target,zone,pants_collision,.020)
        delta=target-current[:half]
        corr=np.linalg.solve(linear[:half],delta[:,:,None])[:,:,0]
        shape=coat.shape_key_add(name=key);shape.data.foreach_set('co',(cp+np.vstack((corr,corr))).astype(np.float32).ravel())
        for o,p,w,tri,abc in details:
            _,lin=deform(p,w,mats);desired=np.einsum('nk,nkj->nj',abc,delta[tri])
            dc=np.linalg.solve(lin,desired[:,:,None])[:,:,0]
            shape=o.shape_key_add(name=key);shape.data.foreach_set('co',(p+dc).astype(np.float32).ravel())
        print('RESEARCHER_WAIST_BAKED',role,frame,flush=True)
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for o in [coat]+[d[0] for d in details]:
    for key in o.data.shape_keys.key_blocks:key.value=0
scene.frame_set(0);bpy.context.view_layer.update()
(ROOT/'waist_curves.json').write_text(json.dumps(curves),encoding='utf-8')
(ROOT/'waist_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V03.blend'))
export=(TOOLS/'export_delivery.py').read_text(encoding='utf-8').replace('FacelessResearcher20261009/V01','FacelessResearcher20261009/V03').replace("replace('V04','V01')","replace('V04','V03')")
exec(compile(export,'researcher_v03_export','exec'))
