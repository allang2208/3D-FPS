"""Author two full-body carry clips on the intact Epic Quinn skeleton.

Source FBXs are immutable. No mesh edits, retopology, donor limbs or cloth.
The native animation graph owns stride shortening and ground adaptation.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchFoundation20260920')
OUT=ROOT/'Authoring'; OUT.mkdir(exist_ok=True)
DEL=ROOT/'Delivery'; DEL.mkdir(exist_ok=True)
SOURCE=json.loads((ROOT/'source_motion.json').read_text())
Z=Vector((0,0,1)); FORWARD=Vector((0,-1,0))
clips={}

def update(): bpy.context.view_layer.update()
def world(rig,name): return rig.matrix_world@rig.pose.bones[name].matrix
def set_world(rig,name,m):
    rig.pose.bones[name].matrix=rig.matrix_world.inverted()@m
    update()
def rotate_world(rig,name,q):
    m=world(rig,name); p=m.translation.copy()
    m=q.to_matrix().to_4x4()@m; m.translation=p
    set_world(rig,name,m)
def basis(across,along):
    a=across.normalized(); d=(along-a*along.dot(a)).normalized()
    return Matrix((a,d,a.cross(d))).transposed()

for role in ('Idle','Walk'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'Sources'/(role+'.fbx')))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    scene=bpy.context.scene; scene.render.fps=30
    count=int(SOURCE[role]['frames'])+1
    frames=[]; ball={s:[] for s in ('l','r')}
    for frame in range(1,count+1):
        scene.frame_set(frame)
        frames.append((rig.matrix_world.copy(),{b.name:b.matrix_basis.copy() for b in rig.pose.bones}))
        for s in ball: ball[s].append(world(rig,'ball_'+s).translation.copy())
    # Root-motion ball velocity identifies real support phases before travel is removed.
    curves={}
    for s,positions in ball.items():
        values=[]
        for i,p in enumerate(positions):
            lo=max(0,i-1); hi=min(count-1,i+1)
            speed=(positions[hi]-positions[lo]).length*100*30/max(1,hi-lo)
            values.append(speed)
        if role=='Walk': values[-1]=values[0]
        curves['FootSpeed_'+s]=values
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'Sources/Quinn.fbx'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    # Keep the entire original LOD0, with its original weights and topology.
    for o in list(bpy.context.scene.objects):
        if o.type=='MESH' and not o.name.endswith('LOD0'): bpy.data.objects.remove(o,do_unlink=True)
    rig.animation_data_clear()
    scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1;scene.frame_end=count
    rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
    anatomy={}
    for s in ('l','r'):
        hand=rest['hand_'+s].translation
        across=(rest['index_01_'+s].translation-rest['pinky_01_'+s].translation).normalized()
        along=(rest['middle_01_'+s].translation-hand).normalized()
        anatomy[s]=(across,along)
    grip_frames={}
    for frame,(root_matrix,poses) in enumerate(frames,1):
        scene.frame_set(frame)
        # Root stays at the origin; original pelvis sway, rotation and lift survive.
        root_matrix=root_matrix.copy();root_matrix.translation.x=0;root_matrix.translation.y=0
        rig.matrix_world=root_matrix
        for b in rig.pose.bones:
            b.rotation_mode='QUATERNION';b.matrix_basis=poses[b.name]
        update()
        # Distributed, small forward lean; no upper/lower-body donor splice.
        for name,degrees in (('spine_02',3),('spine_04',4),('neck_01',-3)):
            rotate_world(rig,name,Quaternion((1,0,0),math.radians(degrees)))
        pelvis=world(rig,'pelvis').translation
        torso=world(rig,'spine_05').to_quaternion()@rest['spine_05'].to_quaternion().inverted()
        for s,sign in (('l',1),('r',-1)):
            upper='upperarm_'+s;lower='lowerarm_'+s;hand='hand_'+s
            shoulder=world(rig,upper).translation.copy()
            # Small carry motion follows the chest, rather than a frozen global hand.
            target=pelvis+torso@Vector((sign*.30,-.29,.205 if s=='l' else .14))
            a=(rest[lower].translation-rest[upper].translation).length
            b=(rest[hand].translation-rest[lower].translation).length
            direction=(target-shoulder).normalized();dist=min((target-shoulder).length,a+b-.025)
            target=shoulder+direction*dist
            pole=Vector((sign, .42, -.1));pole=(pole-direction*pole.dot(direction)).normalized()
            reach=(a*a-b*b+dist*dist)/(2*dist)
            elbow=shoulder+direction*reach+pole*math.sqrt(max(0,a*a-reach*reach))
            across,along=anatomy[s]
            desired_along=(torso@FORWARD).normalized()
            desired_across=(torso@Z).normalized()
            hand_q=(basis(desired_across,desired_along)@basis(across,along).inverted()).to_quaternion()
            palm=Vector((-sign,0,0)); palm=(torso@palm).normalized()
            for name,end,child in ((upper,elbow,lower),(lower,target,hand)):
                start=world(rig,name).translation
                source_dir=(rest[child].translation-rest[name].translation).normalized()
                dest_dir=(end-start).normalized()
                q=source_dir.rotation_difference(dest_dir)
                if name==lower:
                    # Carry the forearm roll with the hand to avoid concentrating it at the wrist.
                    src_palm=(along.cross(across))*(1 if s=='l' else -1)
                    v=q@src_palm;v=(v-dest_dir*v.dot(dest_dir)).normalized()
                    w=palm-dest_dir*palm.dot(dest_dir);w.normalize()
                    roll=math.atan2(dest_dir.dot(v.cross(w)),v.dot(w))
                    q=Quaternion(dest_dir,roll)@q
                m=q.to_matrix().to_4x4()@rest[name];m.translation=start
                set_world(rig,name,m)
            m=hand_q.to_matrix().to_4x4()@rest[hand];m.translation=target
            set_world(rig,hand,m)
            # Full articulated fingers, reset from reference before cylinder grasp.
            for finger in ('index','middle','ring','pinky','thumb'):
                for segment in ('metacarpal','01','02','03'):
                    n=finger+'_'+segment+'_'+s
                    if n in rig.pose.bones: rig.pose.bones[n].matrix_basis=Matrix.Identity(4)
            update()
            for finger,factor in (('index',.95),('middle',1),('ring',1.02),('pinky',1.03)):
                for segment,degrees in (('01',52),('02',68),('03',35)):
                    rotate_world(rig,finger+'_'+segment+'_'+s,
                        Quaternion(desired_across,math.radians(-sign*degrees*factor)))
            grip=target+desired_along*.071+palm*.022
            # Thumb opposition is an actual joint chain, reaching across the shaft.
            thumb_tip=rig.data.bones['thumb_03_'+s].tail_local.copy()
            tip_local=rig.data.bones['thumb_03_'+s].matrix_local.inverted()@thumb_tip
            thumb_target=grip+desired_across*.021+desired_along*.016-palm*.006
            for iteration in range(6):
                for n in ('thumb_02_'+s,'thumb_01_'+s):
                    pivot=world(rig,n).translation
                    tip=(world(rig,'thumb_03_'+s)@tip_local)
                    v=tip-pivot;w=thumb_target-pivot
                    if v.length>1e-5 and w.length>1e-5:
                        rotate_world(rig,n,v.rotation_difference(w))
            # Export two attachment bones directly, avoiding guessed UE wrist axes.
            grip_frames.setdefault(s,[]).append((grip.copy(),desired_across.copy(),desired_along.copy()))
        # IK tracks follow authored FK exactly before native warping.
        for s in ('l','r'):
            set_world(rig,'ik_foot_'+s,world(rig,'foot_'+s))
            set_world(rig,'ik_hand_'+s,world(rig,'hand_'+s))
        for b in rig.pose.bones:
            b.keyframe_insert('location',frame=frame)
            b.keyframe_insert('rotation_quaternion',frame=frame)
            b.keyframe_insert('scale',frame=frame)
        rig.keyframe_insert('location',frame=frame)
        rig.keyframe_insert('rotation_euler',frame=frame)
        rig.keyframe_insert('scale',frame=frame)
    rig.animation_data.action.name='A_WitchFoundation_'+role
    # Grip local frame is constant relative to the authored hand, used by UE sockets.
    scene.frame_set(1);update()
    grip_info={}
    for s in ('l','r'):
        grip,up,fwd=grip_frames[s][0]
        inv=world(rig,'hand_'+s).inverted()
        grip_info[s]={'point_hand_local':list(inv@grip),'up_hand_local':list((inv.to_3x3()@up).normalized()),
                      'forward_hand_local':list((inv.to_3x3()@fwd).normalized())}
    # Keep a readable material in the editable source; UE uses its own candidate material.
    mat=bpy.data.materials.new('Foundation_MatteCharcoal');mat.diffuse_color=(.075,.06,.047,1)
    for o in scene.objects:
        if o.type=='MESH':
            o.data.materials.clear();o.data.materials.append(mat)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('WitchFoundation_'+role+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(DEL/('A_WitchFoundation_'+role+'.fbx')),
        use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',
        bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,
        bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS')
    clips[role]={'file':str(DEL/('A_WitchFoundation_'+role+'.fbx')),'frames':count,'fps':30,
                 'duration':(count-1)/30,'curves':curves,'grip':grip_info,
                 'source_root_speed_cm_s':300 if role=='Walk' else 0}
    print('AUTHORED '+role+' '+str(count)+' frames',flush=True)
(OUT/'motion_manifest.json').write_text(json.dumps(clips,indent=2),encoding='utf-8')
print('AUTHORED full Quinn body retained; runtime/user review pending',flush=True)
