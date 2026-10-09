"""Author reaction-specific lab-coat clearance; keep the V01 body and motion shapes."""
from pathlib import Path

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009')
TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
# Reuse the original body registration and detail attachment, without removing
# the 53 already-authored idle/walk/attack shapes.
prefix=(TOOLS/'tailor_motion.py').read_text(encoding='utf-8').split('for o in [coat]+[d[0] for d in details]:')[0]
exec(compile(prefix,'researcher_v01_surface_registration','exec'))
ROOT=BASE/'V02'
source=json.loads((ROOT/'reaction_source.json').read_text(encoding='utf-8'))
pants=bpy.data.objects['Researcher_Trousers'];pp,pw=pack(pants)
pants.data.calc_loop_triangles();phalf=len(pp)//2
pt=np.array([tuple(f.vertices) for f in pants.data.loop_triangles if all(i<phalf for i in f.vertices)])
lower=np.flatnonzero(cp[:half,2]<1.125)
curves={};manifest={}

def tree(points,triangles):
    return BVHTree.FromPolygons([Vector(v) for v in points],triangles.tolist(),all_triangles=True)

def project(points,indices,collision,clearance):
    for i in indices:
        h,n,_,_=collision.find_nearest(Vector(points[i]))
        signed=(Vector(points[i])-h).dot(n)
        if signed<clearance:points[i]+=np.array(n)*(clearance-signed)

for role in ['hit']:
    entry=source['clips'][role]
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=entry['file'],use_anim=True)
    imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
    first,last=map(int,donor.animation_data.action.frame_range)
    fps=scene.render.fps/scene.render.fps_base
    # UE FBX adds a trailing duplicate sample beyond the source play length.
    frames=min(last-first+1,round(entry['duration']*fps)+1)
    inv={n:(donor.matrix_world@donor.data.bones[n].matrix_local).inverted() for n in names}
    # Cover impact, the held sample, and the complete recovery, at every source
    # frame. Runtime uses the same explicit reaction time for bones and curves.
    samples=list(range(frames));keys=['FRS2_'+role+'_%03d'%f for f in samples]
    curves[role]={key:[1. if f==sample else 0. for f in samples] for key,sample in zip(keys,samples)}
    manifest[role]={'frames':frames,'fps':fps,'samples':samples,'duration':entry['duration'],
        'source':entry['source'],'maximum_displacement_m':0.}
    for frame,key in zip(samples,keys):
        scene.frame_set(first+frame);bpy.context.view_layer.update()
        mats=np.array([np.array(donor.matrix_world@donor.pose.bones[n].matrix@inv[n]) for n in names])
        posed,_=deform(bp,bw,mats);posed_pants,_=deform(pp,pw,mats)
        current,linear=deform(cp,cw,mats);target=current[:half].copy()
        hit=np.einsum('nk,nkj->nj',bary,posed[ids])
        rotation=np.einsum('nb,bij->nij',wrap_weights,mats[:,:3,:3])
        ofs=np.einsum('nij,nj->ni',rotation,offset)
        normal=np.cross(posed[ids[:,1]]-posed[ids[:,0]],posed[ids[:,2]]-posed[ids[:,0]])
        normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8)
        dist=(ofs*normal).sum(1);ofs+=normal*np.maximum(0,.006-dist)[:,None]
        target[upper]=hit+ofs
        trousers_tree=tree(posed_pants,pt)
        body_collision=tree(posed,bt)
        initial=target.copy()
        # Project to the clothed leg envelope. Diffuse the correction over the
        # sewn surface, then reapply contact constraints so smoothing cannot
        # shrink the hem back through the trousers.
        project(target,lower,trousers_tree,.016)
        for step in range(10):
            delta=target-initial
            sums=np.column_stack([np.bincount(a,weights=delta[b,c],minlength=half)+np.bincount(b,weights=delta[a,c],minlength=half) for c in range(3)])
            target=initial+.55*delta+.45*sums/np.maximum(degree[:,None],1)
            project(target,lower,trousers_tree,.016)
        project(target,upper,body_collision,.006)
        delta=target-current[:half]
        corr=np.linalg.solve(linear[:half],delta[:,:,None])[:,:,0]
        shape=coat.shape_key_add(name=key)
        shape.data.foreach_set('co',(cp+np.vstack((corr,corr))).astype(np.float32).ravel())
        # Use the coat's bind-space deformation and identical interpolated
        # skin weights so pocket corners do not detach during the hit response.
        for o,p,w,tri,abc in details:
            _,lin=deform(p,w,mats)
            desired=np.einsum('nk,nkj->nj',abc,delta[tri])
            dc=np.linalg.solve(lin,desired[:,:,None])[:,:,0]
            shape=o.shape_key_add(name=key);shape.data.foreach_set('co',(p+dc).astype(np.float32).ravel())
        maximum=float(np.linalg.norm(delta,axis=1).max())
        manifest[role]['maximum_displacement_m']=max(manifest[role]['maximum_displacement_m'],maximum)
        print('RESEARCHER_REACTION_BAKED',role,frame,'displacement_m',round(maximum,5),flush=True)
    action=donor.animation_data.action.copy();action.name='Researcher_SourceHit_V02';action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    track=rig.animation_data.nla_tracks.new();track.name='Source_Hit_V02'
    strip=track.strips.new(action.name,first,action);strip.action_slot=action.slots[0];track.mute=True
    rig.animation_data.action=None
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)

for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for o in [coat]+[d[0] for d in details]:
    for key in o.data.shape_keys.key_blocks:key.value=0
scene.frame_set(0);bpy.context.view_layer.update()
(ROOT/'reaction_curves.json').write_text(json.dumps(curves),encoding='utf-8')
(ROOT/'reaction_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V02.blend'))
export=(TOOLS/'export_delivery.py').read_text(encoding='utf-8').replace('FacelessResearcher20261009/V01','FacelessResearcher20261009/V02').replace("replace('V04','V01')","replace('V04','V02')")
exec(compile(export,'researcher_v02_export','exec'))
