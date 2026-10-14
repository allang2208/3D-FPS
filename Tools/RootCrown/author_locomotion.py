"""Original tripod locomotion on the accepted crown rig; no geometry/skin edits."""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/RootCrown_CrownRig.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
head={n:m.translation.copy() for n,m in rest.items()}
chains=[['Bone_004','Bone_003','Bone_002'],['Bone_008','Bone_007','Bone_006','Bone_005'],['Bone_012','Bone_011','Bone_010','Bone_009']]
centers=[Vector((.085,.365,head['Bone_002'].z)),Vector((-.54,-.04,head['Bone_005'].z)),Vector((.365,-.39,head['Bone_009'].z))]
offsets=[0.,1./3.,2./3.]
scene=bpy.context.scene;scene.render.fps=60
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
rig.animation_data_create()
for pb in rig.pose.bones: pb.rotation_mode='QUATERNION'
STANCE=.72
WORLD_SCALE=350./170.

def hermite(a,b,tangent,u):
    return (2*u**3-3*u*u+1)*a+(u**3-2*u*u+u)*tangent+(-2*u**3+3*u*u)*b+(u**3-u*u)*tangent

def foot_clock(phase):
    if phase<STANCE: return phase-STANCE*.5,0.
    u=(phase-STANCE)/(1.-STANCE)
    return hermite(STANCE*.5,-STANCE*.5,1.-STANCE,u),math.sin(math.pi*u)**2

def solve(chain,base,target,orientation,desired):
    points=[base@head[n] for n in chain]
    lengths=[(head[chain[i+1]]-head[chain[i]]).length for i in range(len(chain)-1)]
    origin=points[0].copy();reach=sum(lengths)*.998
    if (target-origin).length>reach: target=origin+(target-origin).normalized()*reach
    # A consistent upward bend seed prevents a straight imported chain from
    # changing its bend side between frames. Bone lengths remain unchanged.
    for p in points[1:-1]: p.z+=.045
    for _ in range(24):
        points[-1]=target.copy()
        for i in range(len(points)-2,-1,-1):
            points[i]=points[i+1]+(points[i]-points[i+1]).normalized()*lengths[i]
        points[0]=origin.copy()
        for i in range(1,len(points)):
            points[i]=points[i-1]+(points[i]-points[i-1]).normalized()*lengths[i-1]
    for i,n in enumerate(chain[:-1]):
        q=(head[chain[i+1]]-head[n]).rotation_difference(points[i+1]-points[i])
        desired[n]=Matrix.LocRotScale(points[i],q@rest[n].to_quaternion(),Vector((1,1,1)))
    desired[chain[-1]]=Matrix.LocRotScale(points[-1],orientation@rest[chain[-1]].to_quaternion(),Vector((1,1,1)))

def pose(phase,seconds,speed,yaw_rate,idle=False):
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    a=math.tau*phase;desired={}
    moving=not idle
    bob=.008*(1.-math.cos(3*a)) if moving else .0025*math.sin(a)
    roll=math.radians(.8 if moving else .12)*math.sin(a)
    shift=.010*math.sin(a) if moving else 0.
    body=Matrix.Translation(Vector((shift,0,-.03+bob)))@Matrix.Translation(head['Bone_000'])@Matrix.Rotation(roll,4,'Y')@Matrix.Translation(-head['Bone_000'])
    desired['Root']=rest['Root'].copy()
    desired['Bone_000']=body@rest['Bone_000'];desired['Bone_001']=body@rest['Bone_001']
    for chain,center,offset in zip(chains,centers,offsets):
        clock,lift=foot_clock((phase+offset)%1.) if moving else (0.,0.)
        yaw=-math.radians(yaw_rate)*seconds*clock
        orientation=Quaternion((0,0,1),yaw)
        target=orientation@center
        # Blender forward is -Y. A planted foot recedes at the exact source
        # linear/angular speed; swing returns with matching endpoint velocity.
        target.y+=speed*seconds*clock
        target.z=center.z+(.066 if abs(speed)>0 else .050)*lift
        solve(chain,body,target,orientation,desired)
    for pb in rig.pose.bones:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        if n not in desired:
            desired[n]=desired[parent]@rest[parent].inverted()@rest[n] if parent else rest[n].copy()
        axis=None;angle=0.
        if n in ('Stem_Lower','Stem_Upper','Crown_Base'):
            lag={'Stem_Lower':.15,'Stem_Upper':.5,'Crown_Base':.85}[n]
            axis=Vector((1,0,0));angle=math.radians(.4 if idle else 1.4)*math.sin(a-lag)
            if yaw_rate: angle+=math.radians(.4)*math.copysign(1,yaw_rate)*math.sin(a-lag)
        elif n.startswith('Crown_') and n!='Crown_Base':
            _,number,part=n.split('_');theta=math.radians(-25+25*(int(number)-1))
            axis=Vector((-math.sin(theta),0,math.cos(theta)))
            lag={'Base':.6,'Flex':.95,'Rim':1.25}[part]
            angle=math.radians({'Base':.6,'Flex':1.1,'Rim':1.8}[part])*(.45 if idle else 1.)*math.sin(a-lag+int(number)*.16)
        if axis is not None:
            local=rest[n].to_quaternion().inverted()@axis
            desired[n]=desired[n]@Quaternion(local,angle).to_matrix().to_4x4()
        pb.matrix_basis=rest[n].inverted()@rest[parent]@desired[parent].inverted()@desired[n] if parent else rest[n].inverted()@desired[n]
    bpy.context.view_layer.update()

for o in scene.objects: o.select_set(False)
rig.select_set(True)
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=rig
exports=ROOT/'Exports/MotionV01';exports.mkdir(exist_ok=True)
records=[]
# Walk and turn stride lengths are fixed source data, independent of runtime
# speed settings. The game advances one phase from actual displacement/yaw.
for role,seconds,speed,yaw in [('Idle',4.,0.,0.),('Move',.6,150./100./WORLD_SCALE,0.),('TurnLeft',.8,0.,90.),('TurnRight',.8,0.,-90.)]:
    action=bpy.data.actions.new('A_RootCrown_'+role+'_V01');action.use_fake_user=True
    rig.animation_data.action=action
    frames=round(seconds*60);scene.frame_start=1;scene.frame_end=frames+1
    for f in range(frames+1):
        scene.frame_set(f+1);pose((f%frames)/frames,seconds,speed,yaw,role=='Idle')
        for pb in rig.pose.bones:
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=channel,frame=f+1,group=pb.name)
    path=exports/('A_RootCrown_'+role+'_V01.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
    records.append(dict(role=role,seconds=seconds,frames=frames+1,source_speed_cm_s=speed*100*WORLD_SCALE,source_turn_deg_s=yaw,fbx=str(path)))
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/RootCrown_LocomotionV01.blend'))
(ROOT/'Reports/locomotion_manifest.json').write_text(json.dumps(dict(clips=records,stance_ratio=STANCE,phase_offsets=offsets,leg_chains=chains,forward='Blender -Y',height_cm=350,root_motion=False,geometry_and_skin='unchanged',runtime_speed_cm_s=150,runtime_yaw_deg_s=150,rendered=False,tested=False),indent=2),encoding='utf8')
print('ROOT_CROWN_MOTION_EXPORTED',flush=True)
