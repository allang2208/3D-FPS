"""M66-specific planted biped gait on the user's 88-bone rig; no mesh changes."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/LocomotionV02')
SOURCE=ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'
for folder in ['Authoring','Export','Records']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=bpy.data.objects['M66_Body'];scene=bpy.context.scene
scene.render.fps=60;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
rig.animation_data_create();rig.animation_data.action=None
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
def depth(n):return 1+depth(parents[n]) if parents[n] else 0
ordered=sorted(rest,key=depth)
chains=[('L','Bone_012','Bone_011','Bone_010'),('R','Bone_017','Bone_016','Bone_015')]
feet={side:rest[foot].translation.copy() for side,_,_,foot in chains}
centre=(feet['L']+feet['R'])*.5
for f in feet.values():f.y=centre.y
TAU=2*math.pi;DUTY=.62;STRIDE=1.44;TURN=math.radians(60)

def smooth(v):v=max(0.,min(1.,v));return v*v*(3-2*v)
def hermite(a,b,da,db,t):return (2*t**3-3*t*t+1)*a+(t**3-2*t*t+t)*da+(-2*t**3+3*t*t)*b+(t**3-t*t)*db
def rotate(matrix,axis,angle):
    scale=matrix.to_scale()
    result=(Quaternion(axis,angle)@matrix.to_quaternion()).to_matrix().to_4x4()@Matrix.Diagonal((scale.x,scale.y,scale.z,1))
    result.translation=matrix.translation
    return result
def pose_frame(role,phase):
    moving=role!='Idle';turning=role.startswith('Turn');wave=TAU*phase
    breath=math.sin(wave-.38*math.sin(wave)) if not moving else math.sin(wave-.6)*.35
    worlds={}
    for name in ordered:
        world=worlds[parents[name]]@local[name] if parents[name] else local[name].copy()
        if name=='Bone_000':
            world.translation+=Vector((-.040*math.sin(wave) if moving else .007*math.sin(wave),
                .008*math.sin(2*wave) if moving else .004*breath,
                .018*math.cos(2*wave)-.018 if moving else .006*breath))
            world=rotate(world,(0,1,0),(.014 if moving else .004)*math.sin(wave))
        if name in ('Bone_007','Bone_006','Bone_005'):
            lag={'Bone_007':0.,'Bone_006':.25,'Bone_005':.48}[name]
            world=rotate(world,(1,0,0),(.009 if moving else .004)*math.sin(wave-lag))
        if name=='Bone_027':world=rotate(world,(1,0,0),(.065 if moving else .010)*math.sin(wave-.40))
        if name=='Bone_026':world=rotate(world,(1,0,0),(.026 if moving else .006)*math.sin(wave-.78))
        if name=='Bone_036':world=rotate(world,(0,0,1),(.025 if moving else .008)*math.sin(wave-1.10))
        if name in ('Bone_032','Bone_031'):world=rotate(world,(1,0,0),.008*math.sin(wave+.65))
        if name in ('Bone_057','Bone_061','Bone_065','Bone_069','Bone_073'):
            world=world@Matrix.Rotation(.016*math.sin(wave+int(name[-3:])*.31),4,'X')
        if name.startswith('M66_Sac'):
            lag=(.35 if 'Upper' in name else .85)+(0.25 if name.endswith('_R') else 0.)
            pulse=math.sin(wave-lag-.25*math.sin(wave-lag))
            amount=.014 if not moving else .005
            world=world@Matrix.Diagonal((1+amount*pulse,1+amount*.65*pulse,1+amount*pulse,1))
            world=rotate(world,(1,0,0),(.007 if moving else .003)*math.sin(wave-lag-.40))
        if name.startswith('M66_Vent'):
            lag=.8+(0.35 if name.endswith('_Tip') else 0.)
            world=rotate(world,(1,0,0),(.018 if name.endswith('_Tip') else .009)*math.sin(wave-lag))
        worlds[name]=world

    for side,upper,lower,foot in chains:
        p=(phase+(0 if side=='L' else .5))%1.;target=feet[side].copy();roll=0.;foot_yaw=0.
        if moving:
            if p<DUTY:
                displacement=-STRIDE*DUTY*.5+STRIDE*p;lift=0
                angular=TURN*DUTY*.5-TURN*p
            else:
                s=(p-DUTY)/(1-DUTY)
                displacement=hermite(STRIDE*DUTY*.5,-STRIDE*DUTY*.5,STRIDE*(1-DUTY),STRIDE*(1-DUTY),s)
                angular=hermite(-TURN*DUTY*.5,TURN*DUTY*.5,-TURN*(1-DUTY),-TURN*(1-DUTY),s)
                lift=.13*math.sin(math.pi*s)**2
                roll=.10*math.sin(TAU*s)*math.sin(math.pi*s)
            if turning:
                sign=1 if role=='TurnLeft' else -1
                target=centre+Quaternion((0,0,1),angular*sign)@(target-centre)
                foot_yaw=angular*sign
            else:target.y+=displacement
            target.z+=lift
        hip=worlds[upper].translation.copy()
        a=(rest[lower].translation-rest[upper].translation).length
        b=(rest[foot].translation-rest[lower].translation).length
        axis=(target-hip).normalized();dist=min((target-hip).length,a+b-.001)
        # Preserve the source leg's knee plane and bend direction.
        pole=rest[lower].translation-rest[upper].translation
        pole=(pole-axis*pole.dot(axis)).normalized()
        along=(a*a-b*b+dist*dist)/(2*dist);height=math.sqrt(max(0.,a*a-along*along))
        knee=hip+axis*along+pole*height
        for name,start,end in [(upper,hip,knee),(lower,knee,target)]:
            base=worlds[parents[name]]@local[name]
            q=base.to_quaternion();direction=q@Vector((0,1,0))
            q=direction.rotation_difference((end-start).normalized())@q
            worlds[name]=q.to_matrix().to_4x4();worlds[name].translation=start
        q=Quaternion((0,0,1),foot_yaw)@Quaternion((1,0,0),roll)@rest[foot].to_quaternion()
        worlds[foot]=q.to_matrix().to_4x4();worlds[foot].translation=target
        # Descendant heels/toes retain their authored neutral relations.
        for name in ordered:
            cursor=parents[name];under=False
            while cursor:
                if cursor==foot:under=True;break
                cursor=parents[cursor]
            if under:worlds[name]=worlds[parents[name]]@local[name]
    for name in ordered:
        base=worlds[parents[name]]@local[name] if parents[name] else local[name]
        pb=rig.pose.bones[name];pb.rotation_mode='QUATERNION';pb.matrix_basis=base.inverted()@worlds[name]

contracts=[]
for role,seconds in [('Idle',4.8),('Move',2.4),('TurnLeft',2.4),('TurnRight',2.4)]:
    action=bpy.data.actions.new('A_M66_'+role+'_V02');rig.animation_data.action=action
    frames=round(seconds*60);scene.frame_start=0;scene.frame_end=frames
    for frame in range(frames+1):
        scene.frame_set(frame);pose_frame(role,(frame%frames)/frames)
        for pb in rig.pose.bones:
            pb.keyframe_insert('location',frame=frame,group=pb.name)
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
            pb.keyframe_insert('scale',frame=frame,group=pb.name)
    action['loop']=True;action['M66_source']='Original M66-specific authored gait on existing user SmartRig'
    action['M66_stride_cm']=144. if role=='Move' else 0.
    action['M66_turn_degrees']=60. if role.startswith('Turn') else 0.
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
    destination=ROOT/'Export'/('A_M66_'+role+'_V02.fbx')
    bpy.ops.export_scene.fbx(filepath=str(destination),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
        bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
    contracts.append({'role':role,'action':action.name,'fbx':str(destination),'seconds':seconds,'frames':frames+1,'fps':60,
        'stride_cm':144. if role=='Move' else 0.,'turn_degrees':60. if role.startswith('Turn') else 0.,'loop':True})
    print('M66_EXPORTED '+role,flush=True)
rig.animation_data.action=bpy.data.actions['A_M66_Idle_V02']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=288;scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_locomotion_v02.blend'))
manifest={'source':str(SOURCE),'authoring':str(ROOT/'Authoring/M66_locomotion_v02.blend'),'clips':contracts,
    'bones':len(rest),'mesh_modified':False,'stance_fraction':DUTY,'swing_lift_cm':13.,
    'source_walk_speed_cm_s':60.,'runtime_walk_speed_cm_s':80.,'root_motion':False,
    'method':'Original nonlinear body timing, measured two-bone leg IK, planted stance, eased swing and delayed asymmetric arm/sac/vent motion',
    'runtime_tested':False,'rendered':False}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('M66_LOCOMOTION_AUTHORED '+json.dumps({'clips':len(contracts),'bones':len(rest),'source':str(SOURCE)}))
