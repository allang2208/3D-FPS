"""Edit only right index rotation tracks in the two existing reload actions."""
import bpy,json,math
from pathlib import Path
from mathutils import Quaternion,Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4InfimaRigRepair20260909/SK_M4_Infima_RigRepair.blend')
scene=bpy.context.scene;rig=bpy.data.objects['SK_M4_Infima']
BONES=['index_01_r','index_02_r','index_03_r']
def action(a):
    rig.animation_data_create();rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
def frame(t):
    scene.frame_set(int(t),subframe=t-int(t));bpy.context.view_layer.update()
def smooth(x):
    x=max(0,min(1,x));return x*x*(3-2*x)
action(bpy.data.actions['M4_idle']);frame(0)
target={n:rig.pose.bones[n].rotation_quaternion.copy() for n in BONES}
# Use the held pose's knuckle direction, with a relaxed PIP/DIP arc rather than a tight trigger pull.
target['index_02_r']=Quaternion(Vector((0,0,1)),math.radians(60))
target['index_03_r']=Quaternion(Vector((0,0,1)),math.radians(20))
report={}
for key in ['reload','reload_empty']:
    original=bpy.data.actions['M4_'+key];action(original)
    original_matrices=[]
    for t in range(189):
        frame(t);original_matrices.append({b.name:b.matrix_basis.copy() for b in rig.pose.bones})
    start={n:original_matrices[0][n].to_quaternion() for n in BONES}
    end={n:original_matrices[-1][n].to_quaternion() for n in BONES}
    changed=original.copy();changed.name='M4_'+key+'_FingerCurl';changed.use_fake_user=True;action(changed)
    previous={}
    for t in range(189):
        frame(t)
        for n in BONES:
            q=start[n].slerp(target[n],smooth(t/12)) if t<12 else target[n].slerp(end[n],smooth((t-170)/18)) if t>170 else target[n].copy()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();b=rig.pose.bones[n];b.rotation_quaternion=q;b.keyframe_insert('rotation_quaternion',frame=t)
    for layer in changed.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if any('"'+n+'"' in curve.data_path for n in BONES) and curve.data_path.endswith('rotation_quaternion'):
                        for point in curve.keyframe_points:point.interpolation='LINEAR'
    max_unrelated=0;endpoint_error=0
    for t in range(189):
        frame(t)
        for bone in rig.pose.bones:
            error=max(abs(bone.matrix_basis[i][j]-original_matrices[t][bone.name][i][j]) for i in range(4) for j in range(4))
            if bone.name not in BONES:max_unrelated=max(max_unrelated,error)
            elif t in [0,188]:endpoint_error=max(endpoint_error,error)
    assert max_unrelated<1e-6,max_unrelated
    assert endpoint_error<1e-5,endpoint_error
    scene.render.fps=60;scene.frame_start=0;scene.frame_end=188
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/('A_AKM_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    report[key]={'duration':188/60,'frames':189,'changed_bones':BONES,'max_untouched_local_matrix_error':max_unrelated,'endpoint_matrix_error':endpoint_error}
action(bpy.data.actions['M4_reload_FingerCurl']);frame(60)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_Reload_FingerCurl.blend'))
(OUT/'build_report.json').write_text(json.dumps(report,indent=2))
print('M4_RELOAD_FINGER_EXPORT_PASS',json.dumps(report))
