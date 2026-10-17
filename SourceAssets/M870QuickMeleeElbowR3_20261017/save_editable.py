"""Save five editable M870 action timelines, without rendering or modifying meshes."""
import bpy,gzip,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
D=json.loads((O/'animation_patch.json').read_text(encoding='utf-8'))
with gzip.open(O/'inputs.json.gz','rt',encoding='utf-8') as f:U=json.load(f)['weapons']['m870']
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M870LeftArm20261016/M870_LeftArm_Editable.blend'),use_scripts=False)
rig=bpy.data.objects['SK_Super90'];scene=bpy.context.scene;rig.data.pose_position='POSE'
def mat(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
I=Matrix.Identity(4);C=Matrix.Diagonal((100,-100,100,1));Ci=C.inverted()
names=[b.name for b in rig.data.bones]
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
ue_parents={n:p if p in U['names'] else None for n,p in U['parents'].items()}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
ki={n:((C@rest[n]).inverted()@mat(U['rest'][n])).inverted() for n in names}
local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
base={t['bone']:t for t in D['base_tracks']};actions={}
def key(track,index):
    at=0 if len(track['times'])==1 else index*10
    return track['values'][at:at+10]
for family in ['base',*D['profiles']]:
    overlay={} if family=='base' else {t['bone']:t for t in D['profiles'][family]['clip']['tracks']}
    rows=[];previous={}
    for i in range(D['frames']+1):
        world={}
        def bone(n):
            if n in world:return world[n]
            m=mat(key(base[n],i))
            if n in overlay:
                delta=key(overlay[n],i);p,q,s=m.decompose()
                m=Matrix.LocRotScale(p+Vector(delta[:3]),Quaternion((delta[6],*delta[3:6]))@q,s+Vector(delta[7:10]))
            world[n]=(bone(ue_parents[n]) if ue_parents[n] else I)@m
            return world[n]
        for n in U['names']:bone(n)
        author={n:Ci@world[n]@ki[n] for n in names};row={}
        for n in names:
            local=author[parents[n]].inverted()@author[n] if parents[n] else author[n]
            p,q,s=(local_rest[n].inverted()@local).decompose()
            if n in previous and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy();row[n]=(p,q,s)
        rows.append(row)
    action=bpy.data.actions.new('A_M870_QuickMelee_Elbow_R3_'+family);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    for b in rig.pose.bones:
        b.rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
    for n in names:
        for prop,field,count in (('location',0,3),('rotation_quaternion',1,4),('scale',2,3)):
            for axis in range(count):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)];curve.keyframe_points.clear();curve.keyframe_points.add(len(rows))
                curve.keyframe_points.foreach_set('co',[v for i,row in enumerate(rows) for v in (i,row[n][field][axis])])
                for point in curve.keyframe_points:point.interpolation='LINEAR'
                curve.update()
    actions[family]=action;print('M870_EDITABLE_MELEE_ACTION',family,flush=True)
rig.animation_data.action=actions['base'];rig.animation_data.action_slot=actions['base'].slots[0]
scene.render.fps=D['fps'];scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=D['frames'];scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_QuickMelee_Elbow_R3.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'A_M870_QuickMelee_Elbow_R3.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_step=1,bake_anim_simplify_factor=0)
print('M870_EDITABLE_AND_FBX_SAVED',flush=True)
