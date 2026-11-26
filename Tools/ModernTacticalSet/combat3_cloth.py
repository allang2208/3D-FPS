"""Offline cotton settling; the resulting folds are baked into native game meshes."""
import bpy,sys,copy,math,json
from pathlib import Path
import numpy as np
from mathutils import Vector,kdtree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,unit
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';B=S/'CombatShirtR2'
def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)
def normals(p,f):
    n=np.zeros_like(p);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    for k in range(3):np.add.at(n,f[:,k],cross)
    return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
def mesh(name,p,f):
    me=bpy.data.meshes.new(name);me.from_pydata((np.asarray(p)*[.01,-.01,.01]).tolist(),[],f);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
def settle(name,p,f,rest,pins,body,frames=36):
    if name.startswith(('Shirt_','FP_')):raise RuntimeError('Sleeves require combat3_cuff_solver: rest shape keys relocate pinned wrists')
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)
    collider=mesh('NATIVE_BodyCollider',body['positions'],body['triangles']);collider.modifiers.new('SkinCollision','COLLISION');collider.collision.thickness_outer=.0025;collider.collision.thickness_inner=.001;collider.collision.cloth_friction=8
    ob=mesh('SEWN_Cotton_'+name,p,f);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    ob.shape_key_add(name='Basis');key=ob.shape_key_add(name='CutPattern_RestAllowance')
    for v,q in zip(key.data,np.array(rest)*[.01,-.01,.01]):v.co=q
    group=ob.vertex_groups.new(name='SewnAnchors')
    for i,w in enumerate(pins):
        if w>0:group.add([i],float(w),'REPLACE')
    cloth=ob.modifiers.new('OfflineCottonSettling','CLOTH');settings=cloth.settings
    settings.quality=15;settings.mass=.28;settings.air_damping=3;settings.tension_stiffness=18;settings.compression_stiffness=18;settings.shear_stiffness=6;settings.bending_stiffness=.012;settings.tension_damping=6;settings.compression_damping=6;settings.shear_damping=6;settings.bending_damping=.8;settings.vertex_group_mass=group.name;settings.pin_stiffness=1;settings.rest_shape_key=key;settings.time_scale=.8
    cc=cloth.collision_settings;cc.use_collision=True;cc.distance_min=.002;cc.collision_quality=5;cc.use_self_collision=True;cc.self_distance_min=.0025;cc.self_friction=8
    scene=bpy.context.scene;scene.gravity=(0,0,-9.81);scene.render.fps=30;scene.frame_start=1;scene.frame_end=frames;cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=frames
    for frame in range(1,frames+1):
        scene.frame_set(frame);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);result=np.array([v.co[:] for v in ev.data.vertices])*[100,-100,100]
        if not np.isfinite(result).all():raise RuntimeError('Non-finite cloth state')
        if frame%6==0:print('COTTON_SETTLE',name,frame,float(np.max(np.linalg.norm(result-p,axis=1))),flush=True)
    ob.hide_render=True;collider.hide_render=True;finished=mesh('SETTLED_'+name,result,f)
    for face in finished.data.polygons:face.use_smooth=True
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'Simulation'/(name+'.blend')))
    np.savez_compressed(R/'Simulation'/(name+'.npz'),before=p,after=result,triangles=f,pins=pins,rest=rest)
    return result
def shirt(rig):
    d=read(R/'Authored'/f'shirt_cloth_{rig}.json');native=read(R/'Inputs'/f'Body_{rig}.json');p=np.array(d['positions']);f=np.array(d['triangles']);n=len(p)//2;outer=f[(f<n).all(1)];q=p[:n].copy();bones={b['name']:np.array(b['position']) for b in d['bones']};names={b['index']:b['name'] for b in d['bones']}
    arm=np.array([sum(w for bi,w in ws if any(s in names[bi] for s in ['upperarm','lowerarm','hand_','twist'])) for ws in d['weights'][:n]]);pins=1-smooth((arm-.10)/.65);rest=q.copy()
    for side,sign in [('l',1),('r',-1)]:
        ids=np.flatnonzero(q[:,0]*sign>0);a,e,w=[bones[k+'_'+side] for k in ['upperarm','lowerarm','hand']];upper=unit(e-a);axis=unit(w-e);dist=-(q[ids]-w)@axis;cuff=1-smooth((dist-1.0)/3.0);pins[ids]=np.maximum(pins[ids],cuff);along=(q[ids]-e)@axis;mix=smooth((along+3)/6);up=np.outer((q[ids]-a)@upper,upper)*.10;low=(e-a)*.10+np.outer(along,axis)*.14;rest[ids]+=(up*(1-mix[:,None])+low*mix[:,None])*smooth(arm[ids])[:,None]
    edges=np.sort(np.concatenate([outer[:,[0,1]],outer[:,[1,2]],outer[:,[2,0]]]),1);edges,counts=np.unique(edges,axis=0,return_counts=True);border=np.unique(edges[counts==1]);kd=kdtree.KDTree(len(border))
    for i,vi in enumerate(border):kd.insert(Vector(q[vi]),i)
    kd.balance();distance=np.array([kd.find(Vector(v))[2] for v in q]);pins=np.maximum(pins,1-smooth((distance-.8)/2));pins[border]=1
    moved=settle('Shirt_'+rig,q,outer,rest,pins,native)
    nn=normals(moved,outer);thickness=np.linalg.norm(p[:n]-p[n:],axis=1);d['positions']=moved.tolist()+(moved-nn*thickness[:,None]).tolist();dp=np.array(d['positions']);dn=normals(dp,f);d['normals']=dn[f].tolist();d['cloth_production']=dict(method='Offline cloth rest allowance, pinned sewing ends, gravity and native-body collisions',upper_allowance=.10,forearm_allowance=.14,frames=36)
    write(R/'Authored'/f'shirt_cloth_{rig}.json',d)
if __name__=='__main__':
    import runpy,shutil
    runpy.run_path(str(Path(__file__).with_name('combat3_cuff_world.py')),run_name='__main__')
    runpy.run_path(str(Path(__file__).with_name('combat3_cuff_tailor_world.py')),run_name='__main__')
    for rig in ['Jason','Kaitlin']:
        for stem in ['shirt_cloth','shirt_detail','neck_skin']:
            shutil.copy2(R/'CuffRepairR1/Authored'/f'{stem}_{rig}.json',R/'Authored'/f'{stem}_{rig}.json')
