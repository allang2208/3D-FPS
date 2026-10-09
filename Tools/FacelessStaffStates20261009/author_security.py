"""M-03 V12 reactions on the existing ready stance; preserve V11 geometry and core clips."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V12')
SHARED=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessStaffStates20261009')
for p in ['Motion','Logs','Authoring']:(ROOT/p).mkdir(parents=True,exist_ok=True)
source=json.loads((SHARED/'source.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'V11/Authoring/FacelessSecurity_V11.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['root'];rig.animation_data_create();rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
def mat(p,q):return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def smooth(t):
    t=max(0.,min(1.,t));return t*t*t*(10+t*(-15+6*t))
ordered=sorted(rig.pose.bones,key=lambda p:len(p.bone.parent_recursive));unit=float(rig.matrix_world.to_scale().x)
rest={b.name:mat((rig.matrix_world@b.matrix_local).translation,(rig.matrix_world@b.matrix_local).to_quaternion()) for b in rig.data.bones}
def localize(p):return {b.name:p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name].copy() for b in ordered}
restlocal=localize(rest);inverse={n:m.inverted() for n,m in restlocal.items()}
with bpy.data.libraries.load(str(ROOT.parent/'V06/Motion/FacelessSecurity_MaleMotion_V06.blend'),link=False) as (a,b):b.actions=['Security_MaleV06_idle']
ready_action=b.actions[0];rig.animation_data.action=ready_action;rig.animation_data.action_slot=ready_action.slots[0]
scene.frame_set(1);bpy.context.view_layer.update()
ready={p.name:mat((rig.matrix_world@p.matrix).translation,(rig.matrix_world@p.matrix).to_quaternion()) for p in ordered}
ready_local=localize(ready);rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
def frame(p):
    x=(p['upperarm_l'].translation-p['upperarm_r'].translation).normalized()
    z=(p['head'].translation-p['pelvis'].translation).normalized();z=(z-x*z.dot(x)).normalized()
    return Matrix((x,z.cross(x),z)).transposed()
def read_source(entry):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=entry['file'],use_anim=True)
    imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
    first=int(donor.animation_data.action.frame_range[0]);fps=scene.render.fps/scene.render.fps_base
    ref={n:mat((donor.matrix_world@donor.data.bones[n].matrix_local).translation,(donor.matrix_world@donor.data.bones[n].matrix_local).to_quaternion()) for n in rest}
    reg=frame(rest)@frame(ref).transposed();qr=reg.to_quaternion();poses=[]
    for i in range(round(entry['duration']*fps)+1):
        scene.frame_set(first+i);bpy.context.view_layer.update();pose={}
        for pb in ordered:
            n=pb.name;raw=donor.matrix_world@donor.pose.bones[n].matrix
            q=qr@raw.to_quaternion()@ref[n].to_quaternion().inverted()@qr.inverted()@rest[n].to_quaternion()
            p=pose[pb.parent.name]@restlocal[n].translation if pb.parent else rest[n].translation.copy()
            if n=='pelvis':p=rest[n].translation+reg@(raw.translation-ref[n].translation)
            pose[n]=mat(p,q)
        poses.append(pose)
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)
    return poses,fps
# Only rigid boot soles determine upright support; do not floor-clamp a lying body.
sole={s:[rest['foot_'+s].inverted()@(bpy.data.objects['Security_BootSole_'+s].matrix_world@v.co) for v in bpy.data.objects['Security_BootSole_'+s].data.vertices] for s in ['l','r']}
# Use the existing stance's support elevation, preserving the accepted mesh offset.
ready_floor=min((ready['foot_'+s]@v).z for s in sole for v in sole[s])
def ground(pose):
    z=min((pose['foot_'+s]@v).z for s in sole for v in sole[s]);dz=ready_floor-z
    for m in pose.values():m.translation.z+=dz
manifest={'revision':'V12','base_mesh':source['characters']['Security']['mesh'],'preserved_core_clips':source['characters']['Security']['core_clips'],'clips':{}}
for role,entry in source['clips'].items():
    poses,fps=read_source(entry);count=len(poses);start_local=localize(poses[0]);result=[]
    if role in ['hit','dizzy']:
        for original in poses:
            local=localize(original);p={}
            for pb in ordered:
                n=pb.name;base=ready_local[n];q=base.to_quaternion()
                if n.startswith(('spine_','neck_','head','clavicle_','upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_','wrist_')):
                    delta=start_local[n].to_quaternion().inverted()@local[n].to_quaternion()
                    strength=1.1 if role=='hit' and n.startswith('spine_') else 1.
                    if delta.w<0:delta.negate()
                    axis,angle=delta.to_axis_angle();q=q@Quaternion(axis,angle*strength)
                m=mat(base.translation,q);p[n]=p[pb.parent.name]@m if pb.parent else m
            result.append(p)
        # Exact neutral endpoints remove the old Nurse-to-male stance discontinuity.
        result[0]={n:m.copy() for n,m in ready.items()}
        result[-1]={n:m.copy() for n,m in ready.items()}
        if role=='dizzy':
            # Blend the last 0.20 s back to the first sampled sway, retaining the source rhythm.
            for i in range(max(0,count-round(.20*fps)),count):
                a=localize(result[i]);w=smooth((i-(count-1-.20*fps))/(.20*fps));p={}
                for pb in ordered:
                    n=pb.name;m=mat(a[n].translation.lerp(ready_local[n].translation,w),a[n].to_quaternion().slerp(ready_local[n].to_quaternion(),w))
                    p[n]=p[pb.parent.name]@m if pb.parent else m
                result[i]=p
    else:
        result=poses
        if role in ['get_up','prone_get_up']:
            # Keep the floor turn/hand support; only the final standing section joins the ready stance.
            join=entry['duration']-.40
            for i,pose in enumerate(result):
                t=i/fps
                if t<=join:continue
                a=localize(pose);w=smooth((t-join)/.40);p={}
                for pb in ordered:
                    n=pb.name;m=mat(a[n].translation.lerp(ready_local[n].translation,w),a[n].to_quaternion().slerp(ready_local[n].to_quaternion(),w))
                    p[n]=p[pb.parent.name]@m if pb.parent else m
                ground(p);result[i]=p
            result[-1]={n:m.copy() for n,m in ready.items()}
    action=bpy.data.actions.new('Security_V12_'+role);action.use_fake_user=True;rig.animation_data.action=action;last={}
    for i,pose in enumerate(result,1):
        for pb in ordered:
            n=pb.name;desired=pose[pb.parent.name].inverted()@pose[n] if pb.parent else pose[n];basis=inverse[n]@desired;pos,q,_=basis.decompose()
            if n in last and q.dot(last[n])<0:q.negate()
            last[n]=q.copy();pb.rotation_mode='QUATERNION';pb.location=pos/unit;pb.rotation_quaternion=q;pb.scale=(1,1,1)
            pb.keyframe_insert(data_path='location',frame=i,group=n);pb.keyframe_insert(data_path='rotation_quaternion',frame=i,group=n)
    scene.render.fps=round(fps);scene.render.fps_base=1;scene.frame_start=1;scene.frame_end=count
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    file=ROOT/'Motion'/('A_Security_'+role+'_V12.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
    manifest['clips'][role]={'file':str(file),'source':entry['source'],'fps':fps,'frames':count,'duration':(count-1)/fps,'rate_scale':entry['rate_scale']}
    rig.animation_data.action=None
    print('M03_V12_MOTION_EXPORTED',role,count,flush=True)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_States_V12.blend'))
(ROOT/'motion_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('M03_V12_MOTIONS_READY',flush=True)