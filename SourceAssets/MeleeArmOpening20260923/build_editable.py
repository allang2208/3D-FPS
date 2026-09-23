"""Save editable current meshes and corrected actions, without rendering."""
import bpy,json,sys
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from mesh_source import matrix
for variant in ('Standard','LongGrip'):
    out=P/variant;data=json.loads((out/'source.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(out/'SourceArms.fbx'),use_anim=False)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    names=[b.name for b in rig.data.bones if b.name in data['rest']]
    imported={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
    a=np.array([[*imported[n].translation,1] for n in names]);b=np.array([data['rest'][n]['p'] for n in names])
    mapping=np.linalg.lstsq(a,b,rcond=None)[0]
    convert=Matrix.Identity(4)
    for i in range(3):
        for j in range(4):convert[i][j]=float(mapping[j,i])
    inv=convert.inverted();rest={n:matrix(t) for n,t in data['rest'].items()}
    local_rest={b.name:(b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy()) for b in rig.data.bones}
    scene=bpy.context.scene;rig.animation_data_clear()
    for clip in ('Thrust','Overhead','SprintOverhead'):
        source=data['clips'][clip];patch=json.loads((out/(clip+'_patch.json')).read_text())
        action=bpy.data.actions.new('A_RuneSword_'+clip+'_ArmOpeningV1');action.use_fake_user=True
        rig.animation_data_create();rig.animation_data.action=action;previous={}
        scene.render.fps=round(source['intervals']/source['seconds']);scene.render.fps_base=1
        scene.frame_start,scene.frame_end=0,source['intervals']
        for f,(row,correction) in enumerate(zip(source['samples'],patch['samples'])):
            world={n:matrix(t) for n,t in row['world'].items()};fixed={}
            for n in data['parents']:
                parent=data['parents'][n]
                local=matrix(correction['bones'][n]) if n in correction['bones'] else (world[parent].inverted()@world[n] if parent in world else world[n])
                fixed[n]=fixed[parent]@local if parent in fixed else local
            desired={n:inv@fixed[n]@rest[n].inverted()@convert@imported[n] for n in names}
            for bone in rig.pose.bones:
                n=bone.name;parent=bone.parent.name if bone.parent else None
                w=desired.get(n,imported[n]);parent_world=desired.get(parent,imported.get(parent,rig.matrix_world))
                basis=local_rest[n].inverted()@parent_world.inverted()@w
                loc,q,scale=basis.decompose()
                if n in previous and q.dot(previous[n])<0:q.negate()
                previous[n]=q.copy();bone.rotation_mode='QUATERNION'
                bone.location,bone.rotation_quaternion,bone.scale=loc,q,scale
                for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=f,group=n)
        rig.animation_data.action_slot=action.slots[0]
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
        print('ARM_OPENING_EDITABLE_ACTION',variant,clip,flush=True)
    bpy.context.preferences.filepaths.save_version=0
    scene.frame_set(round(1.18*scene.render.fps))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Melee_ArmOpening_Editable.blend'))
print('ARM_OPENING_EDITABLE_COMPLETE',flush=True)
