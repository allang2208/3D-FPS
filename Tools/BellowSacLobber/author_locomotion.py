"""Author grounded idle and four-beat walks on the user's unchanged skin/rig."""
import json, math, struct
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Quaternion

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/BellowSacLobber_source.blend'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH'
          and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
heads = {n: m.translation.copy() for n,m in rest.items()}
chains = {
    'rear_left': ['Bone_009','Bone_008','Bone_007','Bone_006','Bone_005'],
    'front_left': ['Bone_022','Bone_021','Bone_020','Bone_019'],
    'rear_right': ['Bone_015','Bone_014','Bone_013','Bone_012','Bone_011'],
    'front_right': ['Bone_027','Bone_026','Bone_025','Bone_024'],
}
phases = {'rear_left':0., 'front_left':.25, 'rear_right':.5, 'front_right':.75}
scene = bpy.context.scene
scene.render.fps = 60
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
rig.animation_data_create()
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'

def smooth(x):
    return x*x*x*(x*(x*6.-15.)+10.)

def pulse(p):
    p %= 1.
    return smooth(p/.40) if p < .40 else 1.-smooth((p-.40)/.60)

def solve_leg(chain, base_transform, foot_delta, desired):
    # FABRIK preserves every original joint interval, including rear hock.
    points = [base_transform @ heads[n] for n in chain]
    lengths = [(heads[chain[i+1]]-heads[chain[i]]).length for i in range(len(chain)-1)]
    origin = points[0].copy()
    target = heads[chain[-1]] + foot_delta
    reach = sum(lengths)*.995
    if (target-origin).length > reach:
        target = origin + (target-origin).normalized()*reach
    # Start each pose on its anatomical rest bend, never from the previous
    # sample; this keeps the left/right knee and elbow planes consistent.
    for _ in range(16):
        points[-1] = target.copy()
        for i in range(len(points)-2,-1,-1):
            points[i] = points[i+1] + (points[i]-points[i+1]).normalized()*lengths[i]
        points[0] = origin.copy()
        for i in range(1,len(points)):
            points[i] = points[i-1] + (points[i]-points[i-1]).normalized()*lengths[i-1]
        if (points[-1]-target).length < .0001:
            break
    for i,n in enumerate(chain[:-1]):
        direction = heads[chain[i+1]]-heads[n]
        turn = direction.rotation_difference(points[i+1]-points[i])
        desired[n] = Matrix.LocRotScale(points[i],turn @ rest[n].to_quaternion(),Vector((1,1,1)))
    # Plant the whole palm/sole with its original orientation. The terminal
    # toe bone inherits it; no repeated foot spinning or stretched bone scale.
    n = chain[-1]
    desired[n] = Matrix.LocRotScale(points[-1],rest[n].to_quaternion(),Vector((1,1,1)))

def pose(t, duration, speed):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    p = t/duration
    moving = speed > 0.
    breath = pulse(p) if not moving else .5+.5*math.sin(2*math.pi*p-.3)
    desired = {}
    # Tiny pelvis/chest motion under a heavy sac; feet are solved afterwards.
    roll = math.radians(.65)*math.sin(2*math.pi*p) if moving else math.radians(.16)*math.sin(2*math.pi*p)
    height = .009*(1.-math.cos(4*math.pi*p)) if moving else .004*(breath-.5)
    shift = .009*math.sin(2*math.pi*p) if moving else 0.
    pivot = heads['Bone_000']
    body = Matrix.Translation(Vector((shift,0,height))) @ Matrix.Translation(pivot) @ Matrix.Rotation(roll,4,'Y') @ Matrix.Translation(-pivot)
    desired['Bone_000'] = body @ rest['Bone_000']
    chest_tilt = math.radians(.30)*math.sin(4*math.pi*p+.3) if moving else math.radians(.22)*(breath-.5)
    chest_pivot = heads['Bone_001']
    chest = body @ Matrix.Translation(chest_pivot) @ Matrix.Rotation(chest_tilt,4,'X') @ Matrix.Translation(-chest_pivot)
    desired['Bone_001'] = chest @ rest['Bone_001']
    for n in ('Bone_003','Bone_002'):
        desired[n] = chest @ rest[n]
    sac = .006 if moving else .015
    for n,amount in (('Bone_017',.35),('Bone_016',1.)):
        matrix = chest @ rest[n]
        desired[n] = Matrix.LocRotScale(matrix.translation,matrix.to_quaternion(),Vector((1+sac*amount*breath,1+sac*.4*amount*breath,1+sac*amount*breath)))
    # Connected nozzle bones lag the chest by a small amount, without changing
    # the opening, skin weights or the user's bind pose.
    for i,n in enumerate(('Bone_031','Bone_030','Bone_029','Bone_028')):
        parent = rig.data.bones[n].parent.name
        desired[n] = desired[parent] @ rest[parent].inverted() @ rest[n] @ Quaternion((1,0,0),math.radians(.22 if moving else .32)*math.sin(2*math.pi*p-.20*i)).to_matrix().to_4x4()
    for role,chain in chains.items():
        delta = Vector((0,0,0))
        if moving:
            phase = (p + phases[role]) % 1.
            stance = .76
            travel = speed*duration*stance
            if phase < stance:
                # Source faces Blender -Y. During stance, local feet travel
                # backwards at exactly the authored forward root speed.
                delta.y = -travel*.5 + speed*duration*phase
            else:
                u = (phase-stance)/(1.-stance)
                # Cubic Hermite preserves backward contact velocity at both
                # ends; the middle advances rapidly and slows before landing.
                a,b = travel*.5,-travel*.5
                tangent = speed*duration*(1.-stance)
                delta.y = (2*u**3-3*u*u+1)*a + (u**3-2*u*u+u)*tangent + (-2*u**3+3*u*u)*b + (u**3-u*u)*tangent
                delta.z = (.080 if speed>.5 else .055)*math.sin(math.pi*u)**2
        solve_leg(chain,chest,delta,desired)
    # Convert desired component poses analytically, so dependency-graph lag
    # cannot double-apply parent movement while assigning a child world pose.
    for pb in rig.pose.bones:
        n=pb.name
        parent=pb.parent.name if pb.parent else None
        if n not in desired:
            desired[n]=desired[parent] @ rest[parent].inverted() @ rest[n] if parent else rest[n].copy()
        pb.matrix_basis=(rest[n].inverted() @ rest[parent] @ desired[parent].inverted() @ desired[n]) if parent else rest[n].inverted() @ desired[n]
    bpy.context.view_layer.update()

for obj in bpy.context.scene.objects:
    obj.select_set(False)
rig.select_set(True)
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
export_args = dict(use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,
                   use_armature_deform_only=True,axis_forward='-Y',axis_up='Z',
                   apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
                   mesh_smooth_type='FACE',use_mesh_modifiers=False,path_mode='AUTO',
                   bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
                   bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0.0)
rig.animation_data.action = None
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Exports/SK_BellowSacLobber_v01.fbx'),bake_anim=False,**export_args)

clips = [('Idle',4.8,0.),('WalkSlow',1.2,.40),('Move',1.2,.80)]
records=[]
for role,seconds,speed in clips:
    action = bpy.data.actions.new('A_BellowSacLobber_'+role+'_v01')
    action.use_fake_user=True
    rig.animation_data.action=action
    frames=round(seconds*scene.render.fps)
    scene.frame_start=1;scene.frame_end=frames+1
    for f in range(frames+1):
        scene.frame_set(f+1)
        # Make the final sample identical to the first, including breathing.
        pose(0. if f==frames else f/scene.render.fps,seconds,speed)
        for pb in rig.pose.bones:
            pb.keyframe_insert(data_path='location',frame=f+1,group=pb.name)
            pb.keyframe_insert(data_path='rotation_quaternion',frame=f+1,group=pb.name)
            pb.keyframe_insert(data_path='scale',frame=f+1,group=pb.name)
    export_path=ROOT/('Exports/A_BellowSacLobber_'+role+'_v01.fbx')
    bpy.ops.export_scene.fbx(filepath=str(export_path),bake_anim=True,**export_args)
    records.append({'role':role,'seconds':seconds,'fps':scene.render.fps,'frames':frames+1,
                    'source_speed_cm_s':speed*100,'fbx':str(export_path)})

rig.animation_data.action=None
for pb in rig.pose.bones:
    pb.matrix_basis=Matrix.Identity(4)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/BellowSacLobber_locomotion_v01.blend'))

# Extract original embedded texture bytes without re-encoding the user's PBR.
data=(ROOT/'Source/BellowSacLobber_user_rig.glb').read_bytes();offset=12
while offset<len(data):
    size,kind=struct.unpack_from('<II',data,offset);chunk=data[offset+8:offset+8+size];offset+=8+size
    if kind==0x4e4f534a:g=json.loads(chunk)
    elif kind==0x004e4942:binary=chunk
material=g['materials'][0];pbr=material['pbrMetallicRoughness']
textures={}
for name,index in [('BaseColor',pbr['baseColorTexture']['index']),('Normal',material['normalTexture']['index']),('MetallicRoughness',pbr['metallicRoughnessTexture']['index'])]:
    source=g['textures'][index]['source'];im=g['images'][source];view=g['bufferViews'][im['bufferView']]
    ext='.png' if im.get('mimeType')=='image/png' else '.jpg'
    path=ROOT/('Textures/T_BellowSacLobber_'+name+ext)
    start=view.get('byteOffset',0);path.write_bytes(binary[start:start+view['byteLength']])
    textures[name]=str(path)
report={'version':1,'source_rig':'SmartRigArmature','skin_and_topology':'preserved',
        'source_actions':[],'motion_source':'original offline authored four-beat crawl; no external donor animation',
        'source_forward':'Blender -Y','height_m':1.7,'loop_clips':records,'textures':textures,
        'leg_chains':chains,'cycle_offsets':phases,'stance_ratio':.76,
        'nominal_walk_cm_s':80,'unaware_walk_cm_s':40,'root_motion':False,
        'runtime_tested':False,'preview_rendered':False}
(ROOT/'Records/locomotion_manifest_v01.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BELLOW_LOCOMOTION_EXPORTED '+json.dumps(report),flush=True)
