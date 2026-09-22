"""Relax the held right arm with asymmetric, continuous carry motion.
Applies once per freshly authored input; preserves lower body and combat clocks.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'DrapeGrip20260922'
def apply():
    for role in ('Idle','Walk','CastPoison','Hit','TurnLeft','TurnRight'):
        path=ROOT/f'Authoring/WitchRebuilt_{role}.blend';bpy.ops.wm.open_mainfile(filepath=str(path))
        s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE')
        if r.get('carry_revision')=='Carry04':continue
        def update():bpy.context.view_layer.update()
        def world(n):return r.matrix_world@r.pose.bones[n].matrix
        def put(n,m):r.pose.bones[n].matrix=r.matrix_world.inverted()@m;update()
        def rotate(n,q):
            m=world(n);p=m.translation.copy();m=q.to_matrix().to_4x4()@m;m.translation=p;put(n,m)
        names=['upperarm_r','lowerarm_r','hand_r','ik_hand_r']+[f'{f}_{i:02d}_r' for f in ('thumb','index','middle','ring','pinky') for i in (1,2,3)]
        source=[]
        for frame in range(s.frame_start,s.frame_end+1):
            s.frame_set(frame);source.append({n:r.pose.bones[n].matrix_basis.copy() for n in names})
        for i,keys in enumerate(source):
            frame=s.frame_start+i;s.frame_set(frame)
            for n,m in keys.items():r.pose.bones[n].matrix_basis=m
            update();phase=2*math.pi*i/max(1,len(source)-1);walk=role in ('Walk','TurnLeft','TurnRight')
            # Small delayed arm motion follows existing gait; the accepted spine,
            # legs, staff hand and foot-contact animation tracks are untouched.
            wave=math.sin(phase-.45)-math.sin(-.45)
            pulse=math.sin(phase)
            shift=Vector((.016,.035,-.032))+Vector((.004*pulse,.011*wave,-.007*pulse))*(1 if walk else .45)
            a,b,c=[world(n) for n in ('upperarm_r','lowerarm_r','hand_r')];p=a.translation;original_hand=c.copy()
            l1=(b.translation-p).length;l2=(c.translation-b.translation).length;target=c.translation+shift
            direction=(target-p).normalized();d=max(abs(l1-l2)+.004,min((target-p).length,(l1+l2)*.97))
            target=p+direction*d;pole=b.translation+Vector((-.018,.01,-.005))-p;pole-=direction*pole.dot(direction);pole.normalize()
            along=(l1*l1-l2*l2+d*d)/(2*d);elbow=p+direction*along+pole*math.sqrt(max(0,l1*l1-along*along))
            rotate('upperarm_r',(b.translation-p).rotation_difference(elbow-p))
            b=world('lowerarm_r');c=world('hand_r');rotate('lowerarm_r',(c.translation-b.translation).rotation_difference(target-b.translation))
            # Compensate the carry palm after IK; let the bottle lean slightly
            # with each step instead of holding an identical locked wrist.
            m=original_hand.copy();m.translation=world('hand_r').translation;put('hand_r',m)
            fore=(world('hand_r').translation-world('lowerarm_r').translation).normalized()
            rotate('hand_r',Quaternion(fore,math.radians(-5+2.8*wave)))
            axis=(world('index_01_r').translation-world('pinky_01_r').translation).normalized()
            rotate('hand_r',Quaternion(axis,math.radians(3+1.8*pulse)))
            # The two supporting fingers breathe a little without losing the
            # index/middle/thumb neck grip. Do not flatten every finger together.
            for finger,amount in [('ring',.035),('pinky',.06),('thumb',.01)]:
                for seg in (1,2,3):
                    n=f'{finger}_{seg:02d}_r';loc,q,scale=keys[n].decompose()
                    loosen=amount*(.5-.5*math.cos(phase))
                    r.pose.bones[n].matrix_basis=Matrix.LocRotScale(loc,q.slerp(Quaternion(),loosen),scale)
            update();put('ik_hand_r',world('hand_r'))
            for n in names:
                bone=r.pose.bones[n];bone.rotation_mode='QUATERNION'
                bone.keyframe_insert('rotation_quaternion',frame=frame)
                if n=='ik_hand_r':bone.keyframe_insert('location',frame=frame)
        r['carry_revision']='Carry04';s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(path))
        bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
        bpy.ops.export_scene.fbx(filepath=str(ROOT/f'Delivery/A_WitchRebuilt_{role}.fbx'),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
            use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,
            bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
        print('Carry04 authored:',role)
    manifest_path=ROOT/'Authoring/motion_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for role in ('Idle','Walk','CastPoison','Hit','TurnLeft','TurnRight'):
        manifest[role]['carry_revision']='Carry04: relaxed right elbow/wrist, gait follow-through and staggered supporting-finger motion; other body tracks retained'
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
if __name__=='__main__':apply()
