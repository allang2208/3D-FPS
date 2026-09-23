"""Save the full corrected Thrust, its skinned mesh and original bind pose."""
import bpy,json,sys
from pathlib import Path
import numpy as np
from mathutils import Matrix
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from diagnose_elbows import matrix,pack,rebuild,PRIOR
for variant in ('Standard','LongGrip'):
    out=P/variant;d=json.loads((PRIOR/variant/'source.json').read_text())
    v1=json.loads((PRIOR/variant/'Thrust_patch.json').read_text());patch=json.loads((out/'Thrust_patch.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(PRIOR/variant/'SourceArms.fbx'),use_anim=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    names=[b.name for b in rig.data.bones if b.name in d['rest']]
    imported={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
    a=np.array([[*imported[n].translation,1] for n in names]);b=np.array([d['rest'][n]['p'] for n in names])
    mapping=np.linalg.lstsq(a,b,rcond=None)[0];convert=Matrix.Identity(4)
    for i in range(3):
        for j in range(4):convert[i][j]=float(mapping[j,i])
    inv=convert.inverted();rest={n:matrix(t) for n,t in d['rest'].items()}
    local_rest={b.name:(b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy()) for b in rig.data.bones}
    scene=bpy.context.scene;rig.animation_data_clear();rig.animation_data_create()
    action=bpy.data.actions.new('A_RuneSword_Thrust_ElbowSupportV1');action.use_fake_user=True;rig.animation_data.action=action
    previous={};scene.render.fps=480;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=patch['intervals']
    for f,(row,old,new) in enumerate(zip(d['clips']['Thrust']['samples'],v1['samples'],patch['samples'])):
        _,current=rebuild(row,old,d['parents']);_,fixed=rebuild({'world':{n:pack(m) for n,m in current.items()}},new,d['parents'])
        desired={n:inv@fixed[n]@rest[n].inverted()@convert@imported[n] for n in names}
        for bone in rig.pose.bones:
            n=bone.name;parent=bone.parent.name if bone.parent else None
            w=desired.get(n,imported[n]);parent_world=desired.get(parent,imported.get(parent,rig.matrix_world))
            basis=local_rest[n].inverted()@parent_world.inverted()@w;p,q,s=basis.decompose()
            if n in previous and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy();bone.rotation_mode='QUATERNION';bone.location,bone.rotation_quaternion,bone.scale=p,q,s
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=f,group=n)
    rig.animation_data.action_slot=action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.frame_set(round(.58*480));bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Thrust_ElbowSupport_Editable.blend'))
    print('THRUST_ELBOW_EDITABLE_SAVED',variant,flush=True)
