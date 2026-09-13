"""Shorten only the return-to-ready tail of the accepted M1911 reloads."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;A=O/'Animations';A.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911Contact20260913/M1911_Contact_Editable.blend'))
except RuntimeError as exc:
    if 'Missing library override hierarchy root data' not in str(exc) or 'SK_M1911_Manny' not in bpy.data.objects:raise
r=bpy.data.objects['SK_M1911_Manny'];r.data.pose_position='POSE';s=bpy.context.scene
names=[b.name for b in r.data.bones]
def pose(action,t):
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    f=t*60;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    return {b.name:b.matrix_basis.decompose() for b in r.pose.bones}
idle=pose(bpy.data.actions['M1911_Contact_idle'],0)
records={}
for kind,start,end in [('reload',1.60,1.75),('reload_empty',2.10,2.25)]:
    source=bpy.data.actions['M1911_Contact_'+kind];rows=[];previous={}
    frames=[i*.5 for i in range(round(end*120)+1)]
    for f in frames:
        t=f/60;p=pose(source,t);u=max(0.,min(1.,(t-start)/(end-start)));weight=u*u*(3-2*u)
        row={}
        for n,(loc,q,scale) in p.items():
            # All bones use the same late-tail blend, keeping hand/weapon
            # contact while removing slow drift after the support hand returns.
            target=idle[n];loc=loc.lerp(target[0],weight);q=q.slerp(target[1],weight);scale=scale.lerp(target[2],weight)
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        rows.append(row)
    action=bpy.data.actions.new('M1911_ReloadReady_'+kind);action.use_fake_user=True;r.animation_data.action=action
    for n in names:
        b=r.pose.bones[n];b.rotation_mode='QUATERNION'
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
    for n in names:
        for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(frames))
                c.keyframe_points.foreach_set('co',[v for f,row in zip(frames,rows) for v in (f,row[n][field][axis])])
                for key in c.keyframe_points:key.interpolation='LINEAR'
                c.update()
    r.animation_data.action_slot=action.slots[0];s.frame_start=0;s.frame_end=round(end*60);s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    file=A/('A_M1911_'+kind+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
    records[kind]={'source_action':source.name,'action':action.name,'unchanged_until_seconds':start,'duration':end,'sample_rate':120,'fbx':str(file),'source_duration':float(source.frame_range[1]-source.frame_range[0])/60}
    print('M1911_READY_RELOAD_EXPORTED',kind,end,flush=True)
(O/'authoring.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
pose(bpy.data.actions['M1911_ReloadReady_reload'],0);s.frame_end=105
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_ReloadReady_Editable.blend'))
print('M1911_READY_RELOAD_AUTHORING_COMPLETE',flush=True)
