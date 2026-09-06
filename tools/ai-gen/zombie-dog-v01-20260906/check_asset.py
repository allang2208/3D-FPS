"""Re-import both actual game exports and compare the inherited skeleton motion."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
R=Path(__file__).resolve().parent
def sample(path,candidate=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.context.scene;s.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(path))
    a=next(o for o in s.objects if o.type=='ARMATURE')
    for tr in a.animation_data.nla_tracks:tr.mute=True
    meshes=[o for o in s.objects if o.type=='MESH' and any(mod.type=='ARMATURE' and mod.object==a for mod in o.modifiers)]
    errors=[]
    for m in meshes:
        for v in m.data.vertices:
            values=[g.weight for g in v.groups if g.weight>1e-8]
            assert values and len(values)<=4,(m.name,v.index,len(values))
            errors.append(abs(sum(values)-1))
        if candidate and m.name.startswith('ZombieDog'):
            assert len(m.data.uv_layers)>0
            assert all(math.isfinite(c) for l in m.data.uv_layers.active.data for c in l.uv)
    assert max(errors)<1e-5,max(errors)
    clips={};sampled={};extents={};samples=0
    for act in bpy.data.actions:
        a.animation_data.action=act
        if act.slots:a.animation_data.action_slot=act.slots[0]
        start,end=act.frame_range;duration=(end-start)/30
        clips[act.name]=duration
        low=1e9;high=-1e9
        poses=[]
        for i in range(round(duration*60)+1):
            frame=start+min(i/60,duration)*30
            s.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
            poses.append({b.name:list((a.matrix_world@b.matrix).translation) for b in a.pose.bones})
            if candidate:
                for m in meshes:
                    ev=m.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
                    for v in mesh.vertices:
                        co=ev.matrix_world@v.co
                        assert all(math.isfinite(c) for c in co),(act.name,i,m.name)
                        assert max(abs(c) for c in co)<12,(act.name,i,m.name,list(co))
                        low=min(low,co.z);high=max(high,co.z)
                    ev.to_mesh_clear()
            samples+=1
        sampled[act.name]=poses
        extents[act.name]=[low,high]
    return {'clips':clips,'samples':sampled,'bone_count':len(a.data.bones),'sample_count':samples,
        'max_weight_error':max(errors),'bounds_z':extents,'mesh_count':len(meshes)}
original=sample(R.parents[2]/'assets/models/wolf_quaternius.gltf')
candidate=sample(R/'zombie-dog-v01.glb',True)
assert original['bone_count']==candidate['bone_count']==51
assert original['clips'].keys()==candidate['clips'].keys()
max_delta=0.
for name,poses in original['samples'].items():
    assert abs(original['clips'][name]-candidate['clips'][name])<1e-5
    other=candidate['samples'][name];assert len(poses)==len(other)
    for p,q in zip(poses,other):
        assert p.keys()==q.keys()
        for bone in p:
            max_delta=max(max_delta,max(abs(x-y) for x,y in zip(p[bone],q[bone])))
assert max_delta<.001,('inherited bone motion',max_delta)
report={k:v for k,v in candidate.items() if k!='samples'}
report['max_inherited_bone_position_error_source_units']=max_delta
report['motion_reauthored']=False
(R/'asset-validation.json').write_text(json.dumps(report,indent=2))
print('ZOMBIE_DOG_VALIDATION_COMPLETE',json.dumps(report))
