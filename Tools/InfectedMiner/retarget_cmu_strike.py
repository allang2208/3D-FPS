"""Retarget a contiguous CMU optical-capture strike; no authored attack IK."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912');O=R/'Candidates/CMU02_07';O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'Review/Hand_UserAccepted_20260912/InfectedMiner_Editable.blend'))
r=bpy.data.objects['MinerRig'];s=bpy.context.scene;s.render.fps=30
idle=bpy.data.actions['A_Miner_Idle'];r.animation_data.action=idle;r.animation_data.action_slot=idle.slots[0];s.frame_set(1);bpy.context.view_layer.update()
grip={b.name:b.matrix_basis.copy() for b in r.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))};tr={b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
bpy.ops.preferences.addon_enable(module='io_anim_bvh');bpy.ops.import_anim.bvh(filepath=str(R/'Reference/CMU/02_07.bvh'),global_scale=1,frame_start=1,use_fps_scale=False,update_scene_fps=False,rotate_mode='QUATERNION',axis_forward='-Z',axis_up='Y');dr=bpy.context.object;src=dr.animation_data.action
s.frame_set(1);bpy.context.view_layer.update();sr={b.name:dr.matrix_world@b.matrix for b in dr.pose.bones};M=Matrix.Diagonal((-1,1,1))
s.frame_set(2);bpy.context.view_layer.update();first=dr.matrix_world@dr.pose.bones['Hips'].matrix;fwd=(first.to_quaternion()@sr['Hips'].to_quaternion().inverted())@Vector((0,-1,0));yaw=math.atan2(fwd.x,-fwd.y);align=Matrix.Rotation(-yaw,3,'Z')
def mirror(m):return M@m@M
def frame(axis,ref):
    y=axis.normalized();x=ref-y*ref.dot(y);x.normalize();return Matrix((x,y,x.cross(y))).transposed()
mapping={'pelvis':'Hips','spine_01':'LowerBack','spine_02':'Spine','spine_03':'Spine','spine_04':'Spine1','spine_05':'Spine1','neck_01':'Neck','neck_02':'Neck1','head':'Head'}
for tn,sn in [('clavicle','Shoulder'),('upperarm','Arm'),('lowerarm','ForeArm'),('hand','Hand'),('thigh','UpLeg'),('calf','Leg'),('foot','Foot'),('ball','ToeBase')]:
    for ts,ss in [('l','Right'),('r','Left')]:mapping[tn+'_'+ts]=ss+sn
tnext={'clavicle':'upperarm','upperarm':'lowerarm','lowerarm':'hand','hand':'middle_01','thigh':'calf','calf':'foot','foot':'ball'}
snext={'clavicle':'Arm','upperarm':'ForeArm','lowerarm':'Hand','hand':'HandIndex1','thigh':'Leg','calf':'Foot','foot':'ToeBase'}
cal={}
for tn,sn in mapping.items():
    stem=tn.rsplit('_',1)[0]
    if stem in tnext:
        side=tn[-1];prefix='Right' if side=='l' else 'Left';td=tr[tnext[stem]+'_'+side].translation-tr[tn].translation;sd=sr[prefix+snext[stem]].translation-sr[sn].translation
        ref=Vector((1,0,0)) if stem=='foot' else Vector((0,-1,0));cal[tn]=mirror(sr[sn].to_quaternion().to_matrix()).transposed()@frame(M@sd,ref)@frame(td,ref).transposed()@tr[tn].to_quaternion().to_matrix()
    else:cal[tn]=mirror(sr[sn].to_quaternion().to_matrix()).transposed()@tr[tn].to_quaternion().to_matrix()
old=bpy.data.actions.get('A_Miner_Attack')
if old:old.name='Rejected_Procedural_V03';old.use_fake_user=False
act=bpy.data.actions.new('A_Miner_Attack');act.use_fake_user=True;act.use_frame_range=True;act.frame_start=1;act.frame_end=67;r.animation_data.action=act
ordered=sorted(r.pose.bones,key=lambda b:len(b.parent_recursive));scale=tr['pelvis'].translation.z/sr['Hips'].translation.z;body=bpy.data.objects['Miner_Retopology']
report={'version':'CMU 02_07 human optical mocap, first complete strike','source':'https://github.com/una-dinosauria/cmu-mocap','source_file':'Reference/CMU/02_07.bvh','source_fps':120,'source_frames_including_added_t_pose':[2,266],'source_seconds':[0,2.2],'seconds':2.2,'frames':66,'contact_time':1.5,'contact_end':1.75,'source_timing_preserved':True,'mirrored_for_left_grip':True,'source_heading_alignment_degrees':math.degrees(-yaw),'custom_attack_ik':False,'minimum_surface_z_m':100,'ground_translation_m':[],'mapping':mapping}
for i in range(67):
    s.frame_set(2+i*4);bpy.context.view_layer.update();source={n:dr.matrix_world@dr.pose.bones[n].matrix for n in set(mapping.values())};desired={tn:(mirror(align@source[sn].to_quaternion().to_matrix())@cal[tn]).to_quaternion() for tn,sn in mapping.items()}
    for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
    for n,m in grip.items():r.pose.bones[n].matrix_basis=m
    bpy.context.view_layer.update();hip_delta=M@(align@(source['Hips'].translation-first.translation))*scale
    for b in ordered:
        if b.name not in desired:continue
        p,q,sc=(r.matrix_world@b.matrix).decompose()
        if b.name=='pelvis':p+=hip_delta
        b.matrix=r.matrix_world.inverted()@Matrix.LocRotScale(p,desired[b.name],sc);bpy.context.view_layer.update()
    for side in ['l','r']:
        lower=r.pose.bones['lowerarm_'+side];hand=r.pose.bones['hand_'+side];lm=r.matrix_world@lower.matrix;hm=r.matrix_world@hand.matrix
        neutral=lm.to_quaternion()@tr[lower.name].to_quaternion().inverted()@tr[hand.name].to_quaternion();dq=hm.to_quaternion()@neutral.inverted();axis=(hm.translation-lm.translation).normalized();v=Vector((dq.x,dq.y,dq.z)).dot(axis);tw=Quaternion((dq.w,axis.x*v,axis.y*v,axis.z*v)).normalized()
        if tw.w<0:tw.negate()
        cached={n:r.matrix_world@r.pose.bones[n].matrix for n in ['lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side]}
        for n,w in [('lowerarm_twist_01_'+side,.67),('lowerarm_twist_02_'+side,.34)]:
            p,q,sc=cached[n].decompose();r.pose.bones[n].matrix=r.matrix_world.inverted()@Matrix.LocRotScale(p,Quaternion().slerp(tw,w)@q,sc)
        bpy.context.view_layer.update()
    ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();z=min((ev.matrix_world@v.co).z for v in me.vertices);ev.to_mesh_clear();lift=.003-z
    pb=r.pose.bones['pelvis'];m=pb.matrix.copy();m.translation+=r.matrix_world.to_3x3().inverted()@Vector((0,0,lift));pb.matrix=m;report['ground_translation_m'].append(lift);report['minimum_surface_z_m']=min(report['minimum_surface_z_m'],z+lift)
    for b in r.pose.bones:
        b.rotation_mode='QUATERNION'
        for ch in ['location','rotation_quaternion','scale']:b.keyframe_insert(ch,frame=i+1)
    if act.slots:r.animation_data.action_slot=act.slots[0]
bpy.data.objects.remove(dr,do_unlink=True);s.frame_start=1;s.frame_end=67;s.frame_set(1)
(O/'attack-authoring.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'InfectedMiner_Editable.blend'))
bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
for o in s.objects:
    if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==r for m in o.modifiers):o.select_set(True)
bpy.context.view_layer.objects.active=r;bpy.ops.export_scene.fbx(filepath=str(O/'A_Miner_Attack.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_mesh_modifiers=True,mesh_smooth_type='FACE')
print('CMU_STRIKE_RETARGETED '+json.dumps(report),flush=True)
