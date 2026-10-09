"""Bake coat clearance shapes for the existing Nurse clips; production, no playback."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V01.blend'))
rig=bpy.data.objects['root'];body=bpy.data.objects['Researcher_CompleteBody'];coat=bpy.data.objects['Researcher_LabCoat_Continuous']
scene=bpy.context.scene;names=[b.name for b in rig.data.bones];ni={n:i for i,n in enumerate(names)}
def pack(o):
    p=np.array([v.co[:] for v in o.data.vertices]);w=np.zeros((len(p),len(names)),np.float32);gn={g.index:g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        for g in v.groups:
            if gn[g.group] in ni:w[v.index,ni[gn[g.group]]]=g.weight
    return p,w
def deform(p,w,m):
    linear=np.einsum('nb,bij->nij',w,m[:,:3,:3]);out=np.einsum('nij,nj->ni',linear,p)+w@m[:,:3,3]
    return out,linear
bp,bw=pack(body);cp,cw=pack(coat);half=int(coat['outer_vertex_count'])
if len(cp)!=half*2:raise RuntimeError('Coat wall pairing changed during production')
body.data.calc_loop_triangles();bt=np.array([tuple(f.vertices) for f in body.data.loop_triangles])
coat.data.calc_loop_triangles();ct=[tuple(f.vertices) for f in coat.data.loop_triangles if all(i<half for i in f.vertices)]
body_tree=BVHTree.FromPolygons([Vector(v) for v in bp],bt.tolist(),all_triangles=True)
coat_tree=BVHTree.FromPolygons([Vector(v) for v in cp[:half]],ct,all_triangles=True)
# Upper cloth is registered once to its actual body triangle. This registration
# follows skinning and supplies a consistent exterior normal throughout motion.
upper=np.flatnonzero(cp[:half,2]>1.05);ids=[];bary=[];offset=[];wrap_weights=[]
for i in upper:
    hit=body_tree.find_nearest(Vector(cp[i]));tri=bt[hit[2]]
    abc=np.array(barycentric_transform(hit[0],*(Vector(bp[k]) for k in tri),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))))
    abc=np.maximum(abc,0);abc/=abc.sum();ids.append(tri);bary.append(abc);offset.append(cp[i]-np.array(hit[0]));wrap_weights.append(abc@bw[tri])
ids=np.array(ids);bary=np.array(bary);offset=np.array(offset);wrap_weights=np.array(wrap_weights)
lower=np.flatnonzero(cp[:half,2]<1.075)
edges=np.array([tuple(e.vertices) for e in coat.data.edges if all(i<half for i in e.vertices)]);a,b=edges.T
degree=np.bincount(np.r_[a,b],minlength=half)
details=[]
for o in scene.objects:
    if o.type!='MESH' or not o.name.startswith(('Researcher_HipPocket','Researcher_ChestPocket','Researcher_ID','Researcher_CentrePlacket','Researcher_CoatButton')):continue
    p,w=pack(o);triangles=[];coords=[]
    for v in p:
        hit=coat_tree.find_nearest(Vector(v));tri=ct[hit[2]]
        abc=np.array(barycentric_transform(hit[0],*(Vector(cp[k]) for k in tri),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))))
        abc=np.maximum(abc,0);abc/=abc.sum();triangles.append(tri);coords.append(abc)
    details.append((o,p,w,np.array(triangles),np.array(coords)))
for o in [coat]+[d[0] for d in details]:
    o.shape_key_clear();o.shape_key_add(name='Basis')
curves={};manifest={};source=json.loads((ROOT/'nurse_source.json').read_text(encoding='utf-8'))
for role in ['idle','walk','attack']:
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(ROOT/'Motion'/('A_Nurse_'+role+'.fbx')),use_anim=True)
    imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
    first,last=map(int,donor.animation_data.action.frame_range);frames=last-first+1;fps=scene.render.fps/scene.render.fps_base
    inv={n:(donor.matrix_world@donor.data.bones[n].matrix_local).inverted() for n in names}
    samples=sorted(set(list(range(0,frames,20 if role=='idle' else 6))+[frames-1]))
    keys=['FRS1_'+role+'_%03d'%f for f in samples]
    curves[role]={key:[float(np.interp(f,samples,[1. if s==sample else 0. for s in samples])) for f in range(frames)] for key,sample in zip(keys,samples)}
    manifest[role]={'frames':frames,'fps':fps,'samples':samples,'source':source['clips'][role]['source'],'duration':source['clips'][role]['duration']}
    for frame,key in zip(samples,keys):
        scene.frame_set(first+frame);bpy.context.view_layer.update()
        mats=np.array([np.array(donor.matrix_world@donor.pose.bones[n].matrix@inv[n]) for n in names])
        posed,_=deform(bp,bw,mats);current,linear=deform(cp,cw,mats);target=current[:half].copy()
        hit=np.einsum('nk,nkj->nj',bary,posed[ids]);rotation=np.einsum('nb,bij->nij',wrap_weights,mats[:,:3,:3]);ofs=np.einsum('nij,nj->ni',rotation,offset)
        normal=np.cross(posed[ids[:,1]]-posed[ids[:,0]],posed[ids[:,2]]-posed[ids[:,0]])
        normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8)
        dist=(ofs*normal).sum(1);ofs+=normal*np.maximum(0,.005-dist)[:,None]
        target[upper]=hit+ofs
        posed_tree=BVHTree.FromPolygons([Vector(v) for v in posed],bt.tolist(),all_triangles=True)
        displacement=np.zeros((half,3));fade=np.clip((1.09-cp[:half,2])/.18,0,1)
        for i in lower:
            h,n,_,_=posed_tree.find_nearest(Vector(target[i]));signed=(Vector(target[i])-h).dot(n)
            if signed<.014:displacement[i]=np.array(n)*min(.075,.014-signed)*fade[i]
        # Diffuse the tailoring response along the sewn surface. Paired inner
        # wall receives exactly the same displacement, retaining real thickness.
        for _ in range(8):
            sums=np.column_stack([np.bincount(a,weights=displacement[b,c],minlength=half)+np.bincount(b,weights=displacement[a,c],minlength=half) for c in range(3)])
            displacement=.5*displacement+.5*sums/np.maximum(degree[:,None],1)
        target+=displacement
        delta=target-current[:half];corr=np.linalg.solve(linear[:half],delta[:,:,None])[:,:,0]
        allcorr=np.vstack((corr,corr));shape=coat.shape_key_add(name=key);shape.data.foreach_set('co',(cp+allcorr).astype(np.float32).ravel())
        for o,p,w,tri,abc in details:
            _,lin=deform(p,w,mats);desired=np.einsum('nk,nkj->nj',abc,delta[tri]);dc=np.linalg.solve(lin,desired[:,:,None])[:,:,0]
            shape=o.shape_key_add(name=key);shape.data.foreach_set('co',(p+dc).astype(np.float32).ravel())
        print('RESEARCHER_TAILOR_FRAME',role,frame,flush=True)
    action=donor.animation_data.action.copy();action.name='Researcher_Nurse_'+role;action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    track=rig.animation_data.nla_tracks.new();track.name='Nurse_'+role;strip=track.strips.new(action.name,first,action);strip.action_slot=action.slots[0];track.mute=True
    rig.animation_data.action=None
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for o in [coat]+[d[0] for d in details]:
    for key in o.data.shape_keys.key_blocks:key.value=0
scene.frame_set(0);bpy.context.view_layer.update()
(ROOT/'corrective_curves.json').write_text(json.dumps(curves),encoding='utf-8')
(ROOT/'corrective_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V01.blend'))
print('RESEARCHER_MOTION_TAILORING_SAVED '+json.dumps({k:len(v['samples']) for k,v in manifest.items()}),flush=True)
