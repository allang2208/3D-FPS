"""Requested checks: original source identity, exported joints and native/flex poses."""
import collections,hashlib,json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
d=read(R/'Authored/ue_leather_boots/Jason.json');old=fit.canonical(read(OLD/'Jason_LeatherBoots.json'));p=np.asarray(d['positions']);f=np.asarray(d['triangles'],int);slots=np.asarray(d['triangle_materials']);report={}
inputs=read(R/'inputs.json');disk=P/'Content'/(inputs['source_asset'].split('.')[0][6:]+'.uasset');assert hashlib.sha256(disk.read_bytes()).hexdigest()==inputs['source_asset_sha256']
assert np.isfinite(p).all() and np.isfinite(d['normals']).all() and np.isfinite(d['uv']).all()
area=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1)*.5
report['source']={'vertices':len(p),'triangles':len(f),'minimum_area_cm2':float(area.min()),'nonfinite':False,'weight_sum_max_error':max(abs(sum(w.values())-1) for w in d['weights'])}
assert area.min()>1e-9 and report['source']['weight_sum_max_error']<1e-5
report['foundations']=[];joints=[];foundation_faces=[]
for part in d['parts']:
    if not part['name'].startswith('BootFoundation'):continue
    ids=np.arange(part['first_triangle'],part['first_triangle']+part['triangles']);fs=f[ids];edges=collections.defaultdict(list)
    for fi,tri in zip(ids,fs):
        for a,b in zip(tri,np.roll(tri,-1)):edges[tuple(sorted((int(a),int(b))))].append(int(fi))
    boundary=sum(len(v)==1 for v in edges.values());nonmanifold=sum(len(v)>2 for v in edges.values());assert boundary==0 and nonmanifold==0
    contact=sorted({v for e,ids2 in edges.items() if 5 in set(slots[ids2]) and set(slots[ids2])&{1,4} for v in e});assert len(contact)==128
    adjacent=collections.defaultdict(set)
    for a,b in edges:adjacent[a].add(b);adjacent[b].add(a)
    todo=[int(fs[0,0])];seen=set(todo)
    while todo:
        for nb in adjacent[todo.pop()]:
            if nb not in seen:seen.add(nb);todo.append(nb)
    assert len(seen)==part['vertices'],'Detached body sections remain'
    assert p[list(seen),2].min()<-2 and p[list(seen),2].max()>38
    # Include the entire flexible ankle in export/pose seam checks, not only
    # the welt: this is the interface that the previous revision missed.
    ankle=sorted(v for v in seen if 7.5<p[v,2]<17)
    joints.extend(contact+ankle[::8]);foundation_faces.extend(ids.tolist());report['foundations'].append(dict(name=part['name'],boundary_edges=boundary,nonmanifold_edges=nonmanifold,connected_components=1,sole_to_cuff_connected=True,upper_welt_shared_vertices=len(contact),ankle_samples=len(ankle[::8])))
assert not any(x['name'].startswith('LeatherShaftWithInnerWall') for x in d['parts'])
report['previous_independent_shaft_removed']=True
paths=read(R/'editable.json');bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=paths['fbx']);meshes=[o for o in bpy.data.objects if o.type=='MESH'];assert len(meshes)==1;ob=meshes[0];me=ob.data;me.calc_loop_triangles()
exported=np.array([[q.x*100,-q.y*100,q.z*100] for q in [ob.matrix_world@v.co for v in me.vertices]])
etree=KDTree(len(exported))
for i,q in enumerate(exported):etree.insert(Vector(q),i)
etree.balance();position_delta=[etree.find(Vector(q))[2] for q in p];assert max(position_delta)<.002
enames={g.index:g.name for g in ob.vertex_groups};ews=[{enames[g.group]:g.weight for g in v.groups if g.weight>1e-7} for v in me.vertices]
seams=[]
for vi in sorted(set(joints)):
    matches=[idx for _,idx,_ in etree.find_range(Vector(p[vi]),.0002)]
    assert matches
    for idx in matches:assert sum(abs(ews[idx].get(n,0)-d['weights'][vi].get(n,0)) for n in set(ews[idx])|set(d['weights'][vi]))<1e-4
    seams.append(matches)
report['fbx']={'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'max_position_delta_cm':max(position_delta),'joint_groups':len(seams),'material_slots':len(me.materials),'rigged':bool(ob.find_armature())}
assert len(me.loop_triangles)==len(f) and len(me.materials)==len(SLOTS) and ob.find_armature()
frames=[('Reference',{})]
inputs=read(P/'SourceAssets/RangerCrouchFit20261021/inputs.json')
for name,clip in inputs['clips'].items():
    for i,s in enumerate(clip['samples']):frames.append((name+'@'+str(i),fit.transforms(d,s['bones'])))
def rotation(pivot,axis,degrees):
    m=Matrix.Translation(Vector(pivot))@Matrix.Rotation(math.radians(degrees),4,Vector(axis))@Matrix.Translation(-Vector(pivot));return np.array(m)
for ankle in (-30,0,30):
    for toe in (-20,0,55):
        tr={}
        for side,sign in [('l',1),('r',-1)]:
            axis=(sign*.9882,-.1533,0);foot=rotation(d['bones']['foot_'+side]['position'],axis,ankle);ball=rotation(d['bones']['ball_'+side]['position'],axis,toe);tr['foot_'+side]=foot;tr['ball_'+side]=foot@ball
        frames.append(('Synthetic_ankle'+str(ankle)+'_toe'+str(toe),tr))
all_names=set().union(*ews);ew={n:np.array([w.get(n,0) for w in ews]) for n in all_names};dw={n:np.array([w.get(n,0) for w in d['weights']]) for n in set().union(*d['weights'])}
def skin(points,weights,trans):
    out=np.zeros_like(points)
    for name,w in weights.items():
        m=trans.get(name,np.eye(4));out+=(points@m[:3,:3].T+m[:3,3])*w[:,None]
    return out
pose_rows=[];worst=0.;ff=f[foundation_faces]
for name,tr in frames:
    ep=skin(exported,ew,tr);q=skin(p,dw,tr);gap=max(float(np.max(np.linalg.norm(ep[group]-ep[group[0]],axis=1))) for group in seams);aa=np.linalg.norm(np.cross(q[ff[:,1]]-q[ff[:,0]],q[ff[:,2]]-q[ff[:,0]]),axis=1)*.5
    assert gap<.002 and np.isfinite(q).all() and aa.min()>1e-10
    pose_rows.append(dict(pose=name,max_exported_joint_gap_cm=gap,minimum_foundation_area_cm2=float(aa.min())));worst=max(worst,gap)
    if name=='Synthetic_ankle30_toe55':np.save(R/'Review/posed_boot_positions.npy',q)
report.update(completed=True,author_sha256=hashlib.sha256((R/'Authored/ue_leather_boots/Jason.json').read_bytes()).hexdigest(),pose_count=len(frames),poses=pose_rows,max_joint_gap_cm=worst,runtime_tested=False)
write(R/'model_check.json',report);print('LEATHER_BOOT_MODEL_CHECK_PASSED',len(frames),'poses; maximum seam gap cm',worst,flush=True)
