"""Author a heavy ape-style claw/recovery and repair the arm's trunk-pinned skin.

Original motion construction: no downloaded Rampage/Ape animation was sampled.
Keep bind, geometry, UVs and all non-target action keys from the saved V6 source.
"""
import ast, bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
V6, V4, V3 = ROOT/'ClawV6', ROOT/'HeroHandV4', ROOT/'RuntimeV3'
DELIVERY = OUT/'Delivery'
(DELIVERY/'Animations').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(V6/'HundredEyedSlag_ClawV6.blend'))
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in scene.objects if o.type == 'MESH')
rig.animation_data.action = None
for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
scene.frame_set(1)
arm = rig.data
rest = {b.name:b.matrix_local.copy() for b in arm.bones}
inv = {n:m.inverted() for n,m in rest.items()}
spec = json.loads((ROOT/'AuthoringV1/skeleton_spec.json').read_text())
byname = {r['name']:r for r in spec}
meta = json.loads((ROOT/'AuthoringV1/source_geometry.json').read_text())
limbs = {}
for key,pad in meta['feet_centres_m'].items():
    kind,side = key.split('.')
    ns = [f'{kind}_{part}.{side}' for part in ('upper','lower','palm')]
    d = {k:Vector(byname[n]['head']) for k,n in zip(('shoulder','elbow','wrist'),ns)}
    d.update(pad=Vector(pad), bones=ns, parent=byname[ns[0]]['parent'])
    d['a'] = (d['elbow']-d['shoulder']).length
    d['b'] = (d['wrist']-d['elbow']).length
    d['axis'] = (d['wrist']-d['shoulder']).normalized()
    pole = d['elbow']-d['shoulder']
    d['pole'] = (pole-d['axis']*pole.dot(d['axis'])).normalized()
    d['min_reach'] = math.sqrt(d['a']**2+d['b']**2+2*d['a']*d['b']*math.cos(math.radians(112)))
    d['max_reach'] = math.sqrt(d['a']**2+d['b']**2+2*d['a']*d['b']*math.cos(math.radians(8)))
    d['toes'] = [r['name'] for r in spec if r['name'].startswith(kind+'_digit_') and r['name'].endswith('.'+side)]
    limbs[key] = d
d = limbs['front.R']
namespace = dict(np=np, math=math, Matrix=Matrix, Vector=Vector, Quaternion=Quaternion,
    arm=arm, rest=rest, inv=inv, limbs=limbs, keys=list(limbs))
for file,wanted in [(V3/'author_runtime.py',{'smooth','step','rotation','around','track','aim','solve'}),
                    (V4/'author_hero_hand.py',{'core'})]:
    for node in ast.parse(file.read_text()).body:
        if isinstance(node,ast.FunctionDef) and node.name in wanted:
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'),namespace)
smooth,step,rotation,around,track,aim,solve,core = [namespace[n] for n in
    ('smooth','step','rotation','around','track','aim','solve','core')]

# Skin by arclength along the actual bent arm, never by distance from the floor.
vertices = np.empty(len(mesh.data.vertices)*3,dtype=np.float32)
mesh.data.vertices.foreach_get('co',vertices)
vertices = vertices.reshape(-1,3)
skin = np.load(V6/'skin_weights.npz')
names = [str(n) for n in skin['bone_names']]
col = {n:i for i,n in enumerate(names)}
rows = np.arange(len(vertices))[:,None]
old = np.zeros((len(vertices),len(names)),dtype=np.float32)
old[rows,skin['indices']] = skin['weights']
helpers = ['front_shoulder.R','front_upper_twist.R','front_lower_twist_01.R',
    'front_lower_twist_02.R','front_elbow_support.R','front_wrist_support.R']
right_names = d['bones']+helpers+d['toes']

def arm_coordinates(limb):
    points = [np.asarray(limb[n]) for n in ('shoulder','elbow','wrist','pad')]
    distances,arcs = [],[]
    cumulative = 0.
    for a,b in zip(points,points[1:]):
        delta = b-a
        length = float(np.linalg.norm(delta))
        t = np.clip(((vertices-a)*delta).sum(1)/(delta@delta),0.,1.)
        distances.append(((vertices-a-t[:,None]*delta)**2).sum(1))
        arcs.append(cumulative+t*length)
        cumulative += length
    at = np.asarray(distances).argmin(0)
    return np.asarray(arcs)[at,np.arange(len(vertices))],np.sqrt(np.asarray(distances).min(0))

arc,distance = arm_coordinates(d)
other_distance = np.minimum.reduce([arm_coordinates(limb)[1] for key,limb in limbs.items() if key!='front.R'])
old_right = old[:,[col[n] for n in right_names]].sum(1)
corridor = (distance < .205)&(distance < other_distance+.01)&(arc>.08)&(vertices[:,1]<-.28)&(vertices[:,0]>-.08)&(vertices[:,2]<.74)
region = corridor | ((old_right>.08)&(vertices[:,0]>-.12)&(vertices[:,2]<.74))

body = old.copy()
body[:,[col[n] for n in right_names]] = 0.
body_sum = body.sum(1,keepdims=True)
empty = body_sum[:,0]<1e-8
body[empty,col['chest']] = 1.
body /= np.maximum(body.sum(1,keepdims=True),1e-8)
elbow = smooth(d['a']-.045,d['a']+.045,arc)
wrist = smooth(d['a']+d['b']-.030,d['a']+d['b']+.025,arc)
limb_weights = np.zeros_like(old)
limb_weights[:,col['front_upper.R']] = (1-elbow)*(1-wrist)
limb_weights[:,col['front_lower.R']] = elbow*(1-wrist)
limb_weights[:,col['front_palm.R']] = wrist
attachment = 1-smooth(.035,.195,arc)
w = old.copy()
w[region] = (limb_weights*(1-attachment[:,None])+body*attachment[:,None])[region]

# The outer shoulder cap blends with the upper arm only at the true attachment.
cap = .12*np.exp(-((vertices-np.asarray(d['shoulder']))**2).sum(1)/(2*.075**2))*region
part = w[:,col['front_upper.R']]*cap
w[:,col['front_upper.R']] -= part
w[:,col['front_shoulder.R']] += part
toe_old = old[:,[col[n] for n in d['toes']]]
toe_total = toe_old.sum(1)
amount = np.minimum(w[:,col['front_palm.R']]*.24,toe_total)*region
w[:,col['front_palm.R']] -= amount
for i,n in enumerate(d['toes']):
    w[:,col[n]] += amount*toe_old[:,i]/np.maximum(toe_total,1e-8)

# Smooth only the shoulder/elbow/wrist transition rings, leaving rigid sections.
edges = np.empty(len(mesh.data.edges)*2,dtype=np.int32)
mesh.data.edges.foreach_get('vertices',edges)
edges = edges.reshape(-1,2)
joint = region & ((arc<.23)|(np.abs(arc-d['a'])<.080)|(np.abs(arc-d['a']-d['b'])<.065))
degree = np.zeros(len(vertices),dtype=np.float32)
np.add.at(degree,edges[:,0],1); np.add.at(degree,edges[:,1],1)
for _ in range(3):
    neighbour = np.zeros_like(w)
    np.add.at(neighbour,edges[:,0],w[edges[:,1]])
    np.add.at(neighbour,edges[:,1],w[edges[:,0]])
    average = neighbour/np.maximum(degree[:,None],1)
    w[joint] = .8*w[joint]+.2*average[joint]
new_indices = np.argpartition(w[region],-4,axis=1)[:,-4:]
new_values = np.take_along_axis(w[region],new_indices,axis=1)
new_values /= np.maximum(new_values.sum(1,keepdims=True),1e-8)
indices,values = skin['indices'].copy(),skin['weights'].copy()
indices[region],values[region] = new_indices,new_values
mesh.vertex_groups.clear()
for i,n in enumerate(names):
    group = mesh.vertex_groups.new(name=n)
    rr,cc = np.nonzero(indices==i)
    for vertex,slot in zip(rr,cc):
        weight = float(values[vertex,slot])
        if weight>1e-6: group.add([int(vertex)],weight,'REPLACE')
for modifier in mesh.modifiers:
    if modifier.type=='ARMATURE': modifier.use_deform_preserve_volume=False
np.savez_compressed(OUT/'skin_weights.npz',bone_names=np.asarray(names),indices=indices,weights=values)
print('APE_V7_ARCLENGTH_SKIN_AUTHORED '+str(int(region.sum())),flush=True)

# One transported bend plane owns both arm segments. The forearm has a single
# elbow hinge, with no independent direction-to-quaternion roll or axial twist.
u0 = (d['elbow']-d['shoulder']).normalized()
l0 = (d['wrist']-d['elbow']).normalized()
n0 = u0.cross(l0).normalized()
rest_bend = u0.angle(l0)

def key(time,upper,bend,flex=0.):
    swing = u0.rotation_difference(Vector(upper).normalized())
    return (time,swing,math.radians(bend),math.radians(flex))

pose_keys = {
    'AttackSweep_R':[
        (0.,Quaternion(),rest_bend,0.),
        key(.20,(.28,-.88,-.15),70,3),
        key(.39,(.16,-.87,.47),78,7),
        key(.53,(.24,-.82,.45),72,5),
        key(.64,(.93,-.25,-.27),25,-5),
        key(.76,(.78,-.20,-.46),48,-2),
        key(.98,(.40,-.81,-.42),65,4),
        key(1.16,(.42,-.71,-.56),70,2),
        (1.4,Quaternion(),rest_bend,0.)],
    'AttackSlam_R':[
        (0.,Quaternion(),rest_bend,0.),
        key(.24,(.32,-.88,-.13),72,3),
        key(.55,(.22,-.64,.74),68,7),
        key(.72,(.24,-.65,.72),68,7),
        key(.89,(.72,-.27,-.64),28,-4),
        key(1.03,(.68,-.30,-.67),30,-2),
        key(1.26,(.35,-.84,-.40),60,4),
        key(1.50,(.42,-.70,-.58),70,2),
        (1.8,Quaternion(),rest_bend,0.)]
}

def sample_joint(role,t):
    keys = pose_keys[role]
    for (ta,qa,ba,fa),(tb,qb,bb,fb) in zip(keys,keys[1:]):
        if t<=tb:
            u = step((t-ta)/(tb-ta))
            if qa.dot(qb)<0: qb=qb.copy(); qb.negate()
            return qa.slerp(qb,u),ba+(bb-ba)*u,fa+(fb-fa)*u
    return keys[-1][1:]

def pose(role,t,duration):
    rise = smooth(.02,.36 if role=='AttackSweep_R' else .52,t)
    release = 1-smooth(.76 if role=='AttackSweep_R' else 1.03,duration,t)
    load = float(rise*release)
    hit = .64 if role=='AttackSweep_R' else .89
    shift = track(t,[(0,(0,0,0)),(hit-.15,(-.012,.030,-.010)),
        (hit,(.025,.018,-.026)),(hit+.20,(.012,.022,-.020)),(duration,(0,0,0))])
    G = around((-.04,0,.66),shift,rotation(0,.012*load,-.030*load))
    target = {n:m.copy() for n,m in rest.items()}
    target.update(core(G,rotation(0,.012*load,.020*load),rotation(0,-.010*load,-.015*load),
        rotation(-.012*load,-.020*load,-.045*load),rotation(0,0,-.012*load)))
    parents = {k:target[limb['parent']]@inv[limb['parent']] for k,limb in limbs.items()}
    lo,hi = -.14,.12
    for k,limb in limbs.items():
        if k=='front.R': continue
        sh = parents[k]@limb['shoulder']
        wr = limb['wrist']
        horizontal,vertical = (sh-wr).to_2d().length,sh.z-wr.z
        lo = max(lo,math.sqrt(max(0.,limb['min_reach']**2-horizontal**2))-vertical)
        hi = min(hi,math.sqrt(max(0.,limb['max_reach']**2-horizontal**2))-vertical)
    dz = max(lo,min(0.,hi)) if lo<=hi else min(0.,hi)
    for n in target:
        if n!='root': target[n].translation.z += dz
    for parent in parents.values(): parent.translation.z += dz
    for k,limb in limbs.items():
        if k=='front.R': continue
        sh,elbow,wrist,_ = solve(limb,parents[k],limb['pad'],Quaternion())
        up,low,palm = limb['bones']
        target[up],target[low] = aim(up,sh,elbow),aim(low,elbow,wrist)
        target[palm] = Matrix.Translation(wrist)@rest[palm].to_3x3().to_4x4()
        for toe in limb['toes']: target[toe]=target[palm]@inv[palm]@rest[toe]

    swing,bend,flex = sample_joint(role,t)
    chest_delta = target['chest'].to_quaternion()@rest['chest'].to_quaternion().inverted()
    upper_delta = chest_delta@swing
    lower_delta = upper_delta@Quaternion(n0,bend-rest_bend)
    shoulder = parents['front.R']@d['shoulder']+chest_delta@Vector((0.,-.018*load,.008*load))
    elbow = shoulder+(upper_delta@u0)*d['a']
    wrist = elbow+(lower_delta@l0)*d['b']
    target['front_upper.R'] = Matrix.LocRotScale(shoulder,upper_delta@rest['front_upper.R'].to_quaternion(),Vector((1,1,1)))
    target['front_lower.R'] = Matrix.LocRotScale(elbow,lower_delta@rest['front_lower.R'].to_quaternion(),Vector((1,1,1)))
    wrist_delta = lower_delta@Quaternion(n0,flex)
    target['front_palm.R'] = Matrix.LocRotScale(wrist,wrist_delta@rest['front_palm.R'].to_quaternion(),Vector((1,1,1)))
    for toe in d['toes']:
        m = target['front_palm.R']@inv['front_palm.R']@rest[toe]
        target[toe] = Matrix.LocRotScale(m.translation,m.to_quaternion()@Quaternion((0,1,0),.10*load),Vector((1,1,1)))
    # Unweighted twist helpers inherit the rigid segment without inferred roll.
    for helper,parent in [('front_upper_twist.R','front_upper.R'),('front_lower_twist_01.R','front_lower.R'),
        ('front_lower_twist_02.R','front_lower.R'),('front_elbow_support.R','front_upper.R'),('front_wrist_support.R','front_lower.R')]:
        target[helper] = target[parent]@inv[parent]@rest[helper]
    cap_delta = chest_delta@swing.slerp(Quaternion(),.80)
    target['front_shoulder.R'] = Matrix.LocRotScale(shoulder,cap_delta@rest['front_shoulder.R'].to_quaternion(),Vector((1,1,1)))
    target['ash_origin'] = target['front_plate']@inv['front_plate']@rest['ash_origin']
    target['attack_origin'] = target['front_palm.R']@inv['front_palm.R']@rest['attack_origin']
    return target

contracts = []
paths = {}
all_contracts = json.loads((V4/'animation_contract.json').read_text())['actions']
for original in all_contracts:
    role = original['name']
    if role not in pose_keys: continue
    c = dict(original)
    c.update(action='A_HundredEyedSlag_'+role+'_V7',file='Animations/A_HundredEyedSlag_'+role+'_V7.fbx',
        intent='Heavy ape-style lift/strike with a single bend plane and outer recovery arc',
        motion_source='Original authored adaptation of heavy long-arm mechanics; no store animation sampled')
    contracts.append(c)
    action = bpy.data.actions.new(c['action'])
    action.use_fake_user = True
    rig.animation_data.action = action
    previous,palms = {},[]
    for frame in range(1,c['end_frame_inclusive']+1):
        target = pose(role,(frame-1)/30.,c['seconds'])
        palms.append(list(target['front_palm.R'].translation))
        for bone in arm.bones:
            basis = inv[bone.name]@rest[bone.parent.name]@target[bone.parent.name].inverted()@target[bone.name] if bone.parent else inv[bone.name]@target[bone.name]
            pb = rig.pose.bones[bone.name]
            pb.rotation_mode = 'QUATERNION'
            pb.matrix_basis = basis
            if bone.name in previous and pb.rotation_quaternion.dot(previous[bone.name])<0: pb.rotation_quaternion.negate()
            previous[bone.name] = pb.rotation_quaternion.copy()
            pb.scale = (1,1,1)
            for channel in ('location','rotation_quaternion','scale'): pb.keyframe_insert(channel,frame=frame)
        if not rig.animation_data.action_slot: rig.animation_data.action_slot=action.slots[0]
    for curve in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves:
        for point in curve.keyframe_points: point.interpolation='LINEAR'
    paths[role] = (np.asarray(palms)*100).tolist()

rig.animation_data.action = None
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
mesh.name = 'SK_HundredEyedSlag_ApeRecoveryV7'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_ApeRecoveryV7.blend'))
options = dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True); mesh.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'SK_HundredEyedSlag_ApeRecoveryV7.fbx'),
    object_types={'ARMATURE','MESH'},bake_anim=False,use_mesh_modifiers=False,
    mesh_smooth_type='OFF',path_mode='AUTO',embed_textures=False,**options)
mesh.select_set(False)
for c in contracts:
    action = bpy.data.actions[c['action']]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_end = c['end_frame_inclusive']
    scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(DELIVERY/c['file']),object_types={'ARMATURE'},bake_anim=True,**options)
(OUT/'animation_contract.json').write_text(json.dumps({'actions':contracts,'targeted_roles':list(pose_keys),
    'bone_count':len(arm.bones),'max_influences':4,'bind_and_geometry_preserved':True},indent=2))
(OUT/'authoring_receipt.json').write_text(json.dumps({'revision':'ApeRecoveryV7',
    'authored_weight_vertices':int(region.sum()),'skin_attachment':'Shoulder arclength, not world-space height',
    'motion_source':'Original authored heavy ape-style attack and recovery; no Rampage/Ape file sampled',
    'arm_rotation':'Shared transported bend plane; independent forearm axial twist removed',
    'palm_paths_cm':paths,'game_triangles':len(mesh.data.polygons),'bone_count':len(arm.bones),
    'preview_rendered':False,'runtime_tested':False},indent=2))
print('APE_RECOVERY_V7_AUTHORED_AND_EXPORTED',flush=True)
