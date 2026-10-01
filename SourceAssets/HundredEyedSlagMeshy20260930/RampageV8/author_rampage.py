"""Adapt real Rampage joint motion and donor skin to the existing slag creature.

The attack choreography comes from Epic clips, not procedural attack keyframes.
Bind, topology, UVs, materials and non-target actions are retained. Support/floor
constraints and reference-pose alignment are explicit target-body adaptations.
"""
import ast, bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
SOURCE = ROOT/'RampageReferenceIntake'
V7 = ROOT/'ApeRecoveryV7'
DELIVERY = OUT/'Delivery'
(DELIVERY/'Animations').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(V7/'HundredEyedSlag_ApeRecoveryV7.blend'))
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1
rig = next(o for o in scene.objects if o.type=='ARMATURE')
mesh = next(o for o in scene.objects if o.type=='MESH')
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
    names = [f'{kind}_{part}.{side}' for part in ('upper','lower','palm')]
    limb = {k:Vector(byname[n]['head']) for k,n in zip(('shoulder','elbow','wrist'),names)}
    limb.update(pad=Vector(pad), bones=names, parent=byname[names[0]]['parent'])
    limb['a'] = (limb['elbow']-limb['shoulder']).length
    limb['b'] = (limb['wrist']-limb['elbow']).length
    limb['axis'] = (limb['wrist']-limb['shoulder']).normalized()
    pole = limb['elbow']-limb['shoulder']
    limb['pole'] = (pole-limb['axis']*pole.dot(limb['axis'])).normalized()
    limb['min_reach'] = math.sqrt(limb['a']**2+limb['b']**2+2*limb['a']*limb['b']*math.cos(math.radians(112)))
    limb['max_reach'] = math.sqrt(limb['a']**2+limb['b']**2+2*limb['a']*limb['b']*math.cos(math.radians(6)))
    limb['toes'] = [r['name'] for r in spec if r['name'].startswith(kind+'_digit_') and r['name'].endswith('.'+side)]
    limbs[key] = limb
d = limbs['front.R']
namespace = dict(np=np,math=math,Matrix=Matrix,Vector=Vector,Quaternion=Quaternion,
    arm=arm,rest=rest,inv=inv,limbs=limbs,keys=list(limbs))
for file,wanted in [(ROOT/'RuntimeV3/author_runtime.py',{'smooth','step','rotation','around','aim','solve'}),
                    (ROOT/'HeroHandV4/author_hero_hand.py',{'core'})]:
    for node in ast.parse(file.read_text()).body:
        if isinstance(node,ast.FunctionDef) and node.name in wanted:
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(file),'exec'),namespace)
smooth,step,rotation,around,aim,solve,core = [namespace[n] for n in ('smooth','step','rotation','around','aim','solve','core')]

def coordinates(vertices, points):
    distances,arcs = [],[]
    cumulative = 0.
    for a,b in zip(points,points[1:]):
        a,b = np.asarray(a),np.asarray(b)
        delta = b-a
        length = float(np.linalg.norm(delta))
        t = np.clip(((vertices-a)*delta).sum(1)/(delta@delta),0.,1.)
        distances.append(((vertices-a-t[:,None]*delta)**2).sum(1))
        arcs.append(cumulative+t*length)
        cumulative += length
    segment = np.asarray(distances).argmin(0)
    return np.asarray(arcs)[segment,np.arange(len(vertices))],np.sqrt(np.asarray(distances).min(0))

# Use the actual donor's skin profile, mapped by shoulder/elbow/wrist arclength.
donor = np.load(SOURCE/'donor_skin.npz')
dv,dw = donor['vertices'],donor['weights']
dn = [str(n) for n in donor['bone_names']]
db = json.loads((SOURCE/'donor_bind.json').read_text())
dp = [db[n]['head'] for n in ('upperarm_r','lowerarm_r','hand_r')]
dp.append(np.mean([db[n]['head'] for n in ('index_01_r','pinky_01_r','thumb_01_r')],axis=0).tolist())
da,dr = coordinates(dv,dp)
dl = [np.linalg.norm(np.asarray(b)-a) for a,b in zip(dp,dp[1:])]
donor_channels = np.zeros((len(dv),6),np.float32)
for i,n in enumerate(dn):
    channel = None
    if n=='clavicle_r': channel = 0
    elif n in ('upperarm_r','bicep_muscle_r','tricep_muscle_r'): channel = 1
    elif n.startswith('upperarm_twist_') and n.endswith('_r'): channel = 2
    elif n=='lowerarm_r': channel = 3
    elif n.startswith('lowerarm_twist_') and n.endswith('_r'): channel = 4
    elif n=='hand_r' or (n.endswith('_r') and n.startswith(('index_','pinky_','thumb_'))): channel = 5
    if channel is not None: donor_channels[:,channel] += dw[:,i]
donor_mass = donor_channels.sum(1)
eligible = (donor_mass>.18)&(dr<.31)&(dv[:,0]<-.12)
# Body influence is preserved in the source shoulder samples, then fades along
# the true shoulder attachment instead of using a world-height skinning rule.
donor_channels[:,0] += np.maximum(0.,1-donor_mass)
sx = np.r_[0,np.cumsum(dl)]
target_points = [np.asarray(d[n]) for n in ('shoulder','elbow','wrist','pad')]
tx = np.r_[0,np.cumsum([np.linalg.norm(b-a) for a,b in zip(target_points,target_points[1:])])]
profile_x = np.linspace(0,tx[-1],96)
profile = np.zeros((len(profile_x),6),np.float32)
mapped_da = np.interp(da,sx,tx)
for i,x in enumerate(profile_x):
    field = np.exp(-((mapped_da-x)/.023)**2)*eligible
    if field.sum()<1e-5:
        closest = np.argsort(np.abs(mapped_da[eligible]-x))[:24]
        profile[i] = donor_channels[eligible][closest].mean(0)
    else:
        profile[i] = (donor_channels*field[:,None]).sum(0)/field.sum()
profile /= np.maximum(profile.sum(1,keepdims=True),1e-8)
(OUT/'donor_weight_profile.json').write_text(json.dumps({'source_mesh':str(SOURCE/'source_fbx/Rampage.fbx'),
    'channels':['shoulder','upper','upper_twist','lower','lower_twist','palm'],
    'target_arclength_m':profile_x.tolist(),'weights':profile.tolist()},indent=2))

v = np.empty(len(mesh.data.vertices)*3,np.float32)
mesh.data.vertices.foreach_get('co',v)
v = v.reshape(-1,3)
skin = np.load(V7/'skin_weights.npz')
names = [str(n) for n in skin['bone_names']]
col = {n:i for i,n in enumerate(names)}
old = np.zeros((len(v),len(names)),np.float32)
old[np.arange(len(v))[:,None],skin['indices']] = skin['weights']
helpers = ['front_shoulder.R','front_upper_twist.R','front_lower_twist_01.R',
           'front_lower_twist_02.R','front_elbow_support.R','front_wrist_support.R']
right_names = d['bones']+helpers+d['toes']
arc,distance = coordinates(v,target_points)
other_distance = np.minimum.reduce([coordinates(v,[np.asarray(l[n]) for n in ('shoulder','elbow','wrist','pad')])[1]
    for k,l in limbs.items() if k!='front.R'])
old_right = old[:,[col[n] for n in right_names]].sum(1)
region = ((distance<.205)&(distance<other_distance+.01)&(arc>.04)&(v[:,1]<-.25)&(v[:,0]>-.1)&(v[:,2]<.78))
region |= (old_right>.08)&(v[:,0]>-.12)&(v[:,2]<.78)
body = old.copy()
body[:,[col[n] for n in right_names]] = 0.
body[body.sum(1)<1e-8,col['chest']] = 1.
body /= np.maximum(body.sum(1,keepdims=True),1e-8)
p = np.column_stack([np.interp(arc,profile_x,profile[:,i]) for i in range(6)])
limb = np.zeros_like(old)
for i,name in [(0,'front_shoulder.R'),(1,'front_upper.R'),(2,'front_upper_twist.R'),
               (3,'front_lower.R'),(5,'front_palm.R')]: limb[:,col[name]] = p[:,i]
lower_t = np.clip((arc-d['a'])/d['b'],0,1)
split = smooth(.20,.75,lower_t)
limb[:,col['front_lower_twist_01.R']] = p[:,4]*(1-split)
limb[:,col['front_lower_twist_02.R']] = p[:,4]*split
# Mid-rotation volume bones receive only a short anatomical joint collar.
for centre,radius,helper in [(d['a'],.040,'front_elbow_support.R'),
                            (d['a']+d['b'],.026,'front_wrist_support.R')]:
    amount = .32*np.exp(-((arc-centre)/radius)**2)
    limb *= 1-amount[:,None]
    limb[:,col[helper]] += amount
attach = 1-smooth(.025,.17,arc)
w = old.copy()
w[region] = (body*attach[:,None]+limb*(1-attach[:,None]))[region]
toe_old = old[:,[col[n] for n in d['toes']]]
toe_mass = toe_old.sum(1)
amount = np.minimum(w[:,col['front_palm.R']]*.18,toe_mass)*region
w[:,col['front_palm.R']] -= amount
for i,n in enumerate(d['toes']): w[:,col[n]] += amount*toe_old[:,i]/np.maximum(toe_mass,1e-8)
indices,values = skin['indices'].copy(),skin['weights'].copy()
idx = np.argpartition(w[region],-4,axis=1)[:,-4:]
val = np.take_along_axis(w[region],idx,axis=1)
val /= np.maximum(val.sum(1,keepdims=True),1e-8)
indices[region],values[region] = idx,val
mesh.vertex_groups.clear()
for i,n in enumerate(names):
    group = mesh.vertex_groups.new(name=n)
    rr,cc = np.nonzero(indices==i)
    for vertex,slot in zip(rr,cc):
        weight = float(values[vertex,slot])
        if weight>1e-6: group.add([int(vertex)],weight,'REPLACE')
np.savez_compressed(OUT/'skin_weights.npz',bone_names=np.asarray(names),indices=indices,weights=values)
palm_vertices = v[(region)&(arc>d['a']+d['b']-.005)]-np.asarray(d['wrist'])
print('RAMPAGE_V8_DONOR_SKIN_AUTHORED '+str(int(region.sum())),flush=True)

# Unreal donor faces +Y, with its right arm at -X. The target faces +X and its
# right arm is -Y. Conjugation also converts the coordinate-system handedness.
C = Matrix(((0,1,0),(1,0,0),(0,0,1)))
sources = {}
for name in ['Idle','Idle_Biped','Attack_Biped_Melee_A','Ability_GroundSmash_Start','Ability_GroundSmash_End']:
    raw = json.loads((SOURCE/'source_motion'/(name+'.json')).read_text())
    frames = []
    for row in raw['frames']:
        frame = {}
        for bone,t in row['component'].items():
            xyzw = t['rotation_xyzw']
            q = Quaternion((xyzw[3],xyzw[0],xyzw[1],xyzw[2]))
            frame[bone] = (C@Vector(t['translation_cm'])*.01,(C@q.to_matrix()@C.transposed()).to_quaternion())
        frames.append(frame)
    sources[name] = dict(frames=frames,seconds=raw['seconds'])

def mix(a,b,f):
    result = {}
    for n,(pa,qa) in a.items():
        pb,qb = b[n]
        if qa.dot(qb)<0: qb=qb.copy();qb.negate()
        result[n] = (pa.lerp(pb,f),qa.slerp(qb,f))
    return result

def sample(name,t):
    src = sources[name]
    x = max(0.,min(src['seconds'],t))*60.
    i = min(len(src['frames'])-1,int(x))
    return mix(src['frames'][i],src['frames'][min(i+1,len(src['frames'])-1)],x-i)

def warp(t,pairs):
    for (a,x),(b,y) in zip(pairs,pairs[1:]):
        if t<=b: return x+(y-x)*max(0.,min(1.,(t-a)/(b-a)))
    return pairs[-1][1]

def source_pose(role,t):
    if role=='AttackSweep_R':
        time = warp(t,[(0,0),(.50,.23),(.73,.39),(1.4,1.)])
        return sample('Attack_Biped_Melee_A',time),sources['Idle_Biped']['frames'][0],
    neutral = sources['Idle']['frames'][0]
    if t<.22: src = mix(neutral,sources['Ability_GroundSmash_Start']['frames'][0],step(t/.22))
    elif t<.72: src = sample('Ability_GroundSmash_Start',(t-.22)/.50*sources['Ability_GroundSmash_Start']['seconds'])
    elif t<.82: src = mix(sources['Ability_GroundSmash_Start']['frames'][-1],sources['Ability_GroundSmash_End']['frames'][0],step((t-.72)/.10))
    elif t<1.04: src = sample('Ability_GroundSmash_End',(t-.82)/.22*.25)
    elif t<1.55: src = sample('Ability_GroundSmash_End',.25+(t-1.04)/.51*.45)
    else: src = neutral
    return src,neutral

def frame_basis(direction,normal):
    direction = direction.normalized()
    normal = (normal-direction*normal.dot(direction)).normalized()
    return Matrix((direction,normal.cross(direction),normal)).transposed().to_quaternion()

u0 = (d['elbow']-d['shoulder']).normalized()
l0 = (d['wrist']-d['elbow']).normalized()
n0 = u0.cross(l0).normalized()
target_upper0,target_lower0 = frame_basis(u0,n0),frame_basis(l0,n0)
rest_bend = u0.angle(l0)

def source_arm(src,neutral):
    us = (src['lowerarm_r'][0]-src['upperarm_r'][0]).normalized()
    ls = (src['hand_r'][0]-src['lowerarm_r'][0]).normalized()
    ub = (neutral['lowerarm_r'][0]-neutral['upperarm_r'][0]).normalized()
    lb = (neutral['hand_r'][0]-neutral['lowerarm_r'][0]).normalized()
    nb = ub.cross(lb).normalized()
    transported = src['upperarm_r'][1]@neutral['upperarm_r'][1].inverted()@nb
    bend = us.angle(ls)
    ns = us.cross(ls)
    if ns.length<1e-5: ns=transported.copy()
    else:
        ns.normalize()
        if ns.dot(transported)<0: ns.negate()
        ns = transported.lerp(ns,float(smooth(math.radians(3),math.radians(12),bend))).normalized()
    signed = math.atan2(ns.dot(us.cross(ls)),us.dot(ls))
    return us,ls,ns,max(math.radians(6),min(math.radians(112),signed)),ub,lb,nb

def axial(q):
    if q.w<0: q=q.copy();q.negate()
    return max(-math.radians(65),min(math.radians(65),2*math.atan2(q.x,q.w)))

def volume_helpers(target,upper_frame,lower_frame,src,neutral,source_upper,source_lower,source_upper0,source_lower0):
    def extra(bone,current,base):
        a = current.inverted()@src[bone][1]
        b = base.inverted()@neutral[bone][1]
        return axial(a@b.inverted())
    upper_axis = target['front_lower.R'].translation-target['front_upper.R'].translation
    lower_axis = target['front_palm.R'].translation-target['front_lower.R'].translation
    ug = upper_frame@target_upper0.inverted()
    lg = lower_frame@target_lower0.inverted()
    for helper,parent,base,angle,axis in [
        ('front_upper_twist.R','front_upper.R',ug,extra('upperarm_twist_01_r',source_upper,source_upper0),upper_axis),
        ('front_lower_twist_01.R','front_lower.R',lg,.5*(extra('lowerarm_r',source_lower,source_lower0)+extra('lowerarm_twist_01_r',source_lower,source_lower0)),lower_axis),
        ('front_lower_twist_02.R','front_lower.R',lg,extra('lowerarm_twist_01_r',source_lower,source_lower0),lower_axis)]:
        p = target[parent]@inv[parent]@rest[helper]
        target[helper] = Matrix.LocRotScale(p.translation,Quaternion(axis.normalized(),angle)@base@rest[helper].to_quaternion(),Vector((1,1,1)))
    for helper,a,b,anchor in [('front_elbow_support.R','front_upper.R','front_lower.R','front_lower.R'),
                              ('front_wrist_support.R','front_lower.R','front_palm.R','front_palm.R')]:
        qa = (target[a]@inv[a]).to_quaternion()
        qb = (target[b]@inv[b]).to_quaternion()
        if qa.dot(qb)<0: qb=qb.copy();qb.negate()
        target[helper] = Matrix.LocRotScale(target[anchor].translation,qa.slerp(qb,.5)@rest[helper].to_quaternion(),Vector((1,1,1)))

def pose(role,t,duration):
    src,neutral = source_pose(role,t)
    active = float(smooth(0,.22 if role=='AttackSlam_R' else .24,t)*(1-smooth(1.55 if role=='AttackSlam_R' else 1.12,duration,t)))
    scale = .74
    movement = (src['pelvis'][0]-neutral['pelvis'][0])*scale*.48
    movement.x=max(-.085,min(.085,movement.x))
    movement.y=max(-.055,min(.055,movement.y))
    movement.z=max(-.10,min(.11,movement.z))
    body_q = {}
    for target_name,source_name,factor in [('pelvis','pelvis',.25),('spine','spine_02',.38),('chest','spine_03',.48)]:
        delta = src[source_name][1]@neutral[source_name][1].inverted()
        if delta.w<0: delta.negate()
        body_q[target_name] = Quaternion().slerp(delta,factor)
    target = core(Matrix.Translation(movement),Quaternion(),Quaternion(),Quaternion(),Quaternion())
    for name in ('pelvis','spine','chest'):
        parent = arm.bones[name].parent.name
        location = (target[parent]@inv[parent]@rest[name]).translation
        target[name] = Matrix.LocRotScale(location,body_q[name]@rest[name].to_quaternion(),Vector((1,1,1)))
    for name in ('carapace','front_plate','shell.L','shell.R'):
        parent = arm.bones[name].parent.name
        target[name] = target[parent]@inv[parent]@rest[name]
    parents = {k:target[l['parent']]@inv[l['parent']] for k,l in limbs.items()}
    # Keep the three other support chains planted within their anatomical reach.
    lo,hi=-.15,.13
    for k,l in limbs.items():
        if k=='front.R': continue
        sh = parents[k]@l['shoulder']
        horizontal,vertical=(sh-l['wrist']).to_2d().length,sh.z-l['wrist'].z
        lo=max(lo,math.sqrt(max(0,l['min_reach']**2-horizontal**2))-vertical)
        hi=min(hi,math.sqrt(max(0,l['max_reach']**2-horizontal**2))-vertical)
    dz=max(lo,min(0.,hi)) if lo<=hi else min(0.,hi)
    for n in target:
        if n!='root': target[n].translation.z+=dz
    for parent in parents.values(): parent.translation.z+=dz
    for k,l in limbs.items():
        if k=='front.R': continue
        sh,el,wr,_ = solve(l,parents[k],l['pad'],Quaternion())
        up,lower,palm=l['bones']
        target[up],target[lower]=aim(up,sh,el),aim(lower,el,wr)
        target[palm]=Matrix.Translation(wr)@rest[palm].to_3x3().to_4x4()
        for toe in l['toes']: target[toe]=target[palm]@inv[palm]@rest[toe]

    us,ls,ns,bend,ub,lb,nb=source_arm(src,neutral)
    su,sl=frame_basis(us,ns),frame_basis(ls,ns)
    su0,sl0=frame_basis(ub,nb),frame_basis(lb,nb)
    alignment = target_upper0@su0.inverted()
    if alignment.w<0: alignment.negate()
    # Neutral-pose alignment is released during the strike, so the source's
    # actual overhead trajectory survives the very different target rest pose.
    alignment = alignment.slerp(Quaternion(),active)
    upper_dir,normal=alignment@us,alignment@ns
    bend += (rest_bend-ub.angle(lb))*(1-active)
    bend=max(math.radians(6),min(math.radians(112),bend))
    lower_dir=Quaternion(normal,bend)@upper_dir
    tfu,tfl=frame_basis(upper_dir,normal),frame_basis(lower_dir,normal)
    source_palm_now=sl.inverted()@src['hand_r'][1]
    source_palm_base=sl0.inverted()@neutral['hand_r'][1]
    palm_q=tfl@source_palm_now@source_palm_base.inverted()@target_lower0.inverted()@rest['front_palm.R'].to_quaternion()

    shoulder = parents['front.R']@d['shoulder']
    # Source clavicle elevation and advance are transferred relative to its
    # chest, rather than dragging the entire arm from an unrelated body frame.
    offset = ((src['upperarm_r'][0]-src['spine_03'][0])-(neutral['upperarm_r'][0]-neutral['spine_03'][0]))*scale*.55
    offset = Vector((max(-.075,min(.075,offset.x)),max(-.055,min(.055,offset.y)),max(-.04,min(.105,offset.z))))*active
    shoulder += offset
    elbow=shoulder+upper_dir*d['a']
    wrist=elbow+lower_dir*d['b']
    # Resolve palm-floor contact with the real target hand's sole extents. This
    # is only a contact correction, and retains the donor's elbow-plane pole.
    palm_delta=palm_q@rest['front_palm.R'].to_quaternion().inverted()
    for contact_iteration in range(4):
        palm_delta=palm_q@rest['front_palm.R'].to_quaternion().inverted()
        floor_wrist=.012-float((palm_vertices@np.asarray(palm_delta.to_matrix()).T)[:,2].min())
        if wrist.z<floor_wrist:
            requested=wrist.copy();requested.z=floor_wrist
            axis=requested-shoulder
            reach=max(d['min_reach'],min(d['max_reach'],axis.length))
            axis.normalize()
            pole=elbow-shoulder-axis*(elbow-shoulder).dot(axis)
            if pole.length<1e-5: pole=normal.cross(axis)
            pole.normalize()
            x=(d['a']**2+reach**2-d['b']**2)/(2*reach)
            h=math.sqrt(max(0.,d['a']**2-x*x))
            elbow=shoulder+axis*x+pole*h
            wrist=shoulder+axis*reach
            upper_dir=(elbow-shoulder).normalized()
            lower_dir=(wrist-elbow).normalized()
            new_normal=upper_dir.cross(lower_dir)
            if new_normal.length>1e-5:
                new_normal.normalize()
                if new_normal.dot(normal)<0:new_normal.negate()
                normal=new_normal
            tfu,tfl=frame_basis(upper_dir,normal),frame_basis(lower_dir,normal)
            palm_q=tfl@source_palm_now@source_palm_base.inverted()@target_lower0.inverted()@rest['front_palm.R'].to_quaternion()
    for bone,location,frame,base,source_bone,current,reference in [
        ('front_upper.R',shoulder,tfu,target_upper0,'upperarm_r',su,su0),
        ('front_lower.R',elbow,tfl,target_lower0,'lowerarm_r',sl,sl0)]:
        current_offset=current.inverted()@src[source_bone][1]
        reference_offset=reference.inverted()@neutral[source_bone][1]
        roll=axial(current_offset@reference_offset.inverted())
        axis=upper_dir if source_bone=='upperarm_r' else lower_dir
        q=Quaternion(axis,roll)@frame@base.inverted()@rest[bone].to_quaternion()
        target[bone]=Matrix.LocRotScale(location,q,Vector((1,1,1)))
    target['front_palm.R']=Matrix.LocRotScale(wrist,palm_q,Vector((1,1,1)))
    for toe in d['toes']:target[toe]=target['front_palm.R']@inv['front_palm.R']@rest[toe]
    cap_q=body_q['chest'].slerp((target['front_upper.R']@inv['front_upper.R']).to_quaternion(),.45)
    target['front_shoulder.R']=Matrix.LocRotScale(shoulder,cap_q@rest['front_shoulder.R'].to_quaternion(),Vector((1,1,1)))
    volume_helpers(target,tfu,tfl,src,neutral,su,sl,su0,sl0)
    for n in ('neck','head','eyes.L','eyes.R'):
        if n in rest:
            parent=arm.bones[n].parent.name
            target[n]=target[parent]@inv[parent]@rest[n]
    target['ash_origin']=target['front_plate']@inv['front_plate']@rest['ash_origin']
    target['attack_origin']=target['front_palm.R']@inv['front_palm.R']@rest['attack_origin']
    return target

contracts=[]
paths={}
for original in json.loads((V7/'animation_contract.json').read_text())['actions']:
    c=dict(original)
    role=c['name']
    c.update(action='A_HundredEyedSlag_'+role+'_RampageV8',file='Animations/A_HundredEyedSlag_'+role+'_RampageV8.fbx',
        motion_source='Epic Rampage Attack_Biped_Melee_A' if role=='AttackSweep_R' else 'Epic Rampage Ability_GroundSmash_Start + Ability_GroundSmash_End',
        intent='Reference-based large-arm lift, strike and recovery with shoulder/torso coordination')
    contracts.append(c)
    action=bpy.data.actions.new(c['action']);action.use_fake_user=True
    rig.animation_data.action=action
    previous,palms,elbows=[],[],[]
    previous={}
    for frame in range(1,c['end_frame_inclusive']+1):
        target=pose(role,(frame-1)/30.,c['seconds'])
        palms.append(list(target['front_palm.R']@inv['front_palm.R']@d['pad']))
        elbows.append(list(target['front_lower.R'].translation))
        for bone in arm.bones:
            if bone.name not in target:
                parent=bone.parent.name if bone.parent else None
                target[bone.name]=target[parent]@inv[parent]@rest[bone.name] if parent else rest[bone.name].copy()
            basis=inv[bone.name]@rest[bone.parent.name]@target[bone.parent.name].inverted()@target[bone.name] if bone.parent else inv[bone.name]@target[bone.name]
            pb=rig.pose.bones[bone.name]
            pb.rotation_mode='QUATERNION';pb.matrix_basis=basis
            if bone.name in previous and pb.rotation_quaternion.dot(previous[bone.name])<0:pb.rotation_quaternion.negate()
            previous[bone.name]=pb.rotation_quaternion.copy()
            pb.scale=(1,1,1)
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame)
        if not rig.animation_data.action_slot:rig.animation_data.action_slot=action.slots[0]
    for curve in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    paths[role]={'palm_cm':(np.asarray(palms)*100).tolist(),'elbow_cm':(np.asarray(elbows)*100).tolist()}

rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
mesh.name='SK_HundredEyedSlag_RampageV8'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_RampageV8.blend'))
options=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'SK_HundredEyedSlag_RampageV8.fbx'),
    object_types={'ARMATURE','MESH'},bake_anim=False,use_mesh_modifiers=False,
    mesh_smooth_type='OFF',path_mode='AUTO',embed_textures=False,**options)
mesh.select_set(False)
for c in contracts:
    action=bpy.data.actions[c['action']]
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_end=c['end_frame_inclusive'];scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(DELIVERY/c['file']),object_types={'ARMATURE'},bake_anim=True,**options)
(OUT/'animation_contract.json').write_text(json.dumps({'actions':contracts,'targeted_roles':['AttackSweep_R','AttackSlam_R'],
    'bone_count':len(arm.bones),'max_influences':4,'bind_and_geometry_preserved':True,
    'source_time_mapping':{'AttackSweep_R':[[0,0],[.50,.23],[.73,.39],[1.4,1.]],
        'AttackSlam_R':'0-.22 intro; .22-.72 GroundSmash_Start; .72-.82 join; .82-1.04 End[0:.25]; 1.04-1.55 End[.25:.7]; 1.55-1.8 neutral'},
    'native_hit_windows_preserved':True},indent=2))
(OUT/'authoring_receipt.json').write_text(json.dumps({'revision':'RampageV8','motion_source':'Actual Epic Rampage source joint rotations and component motion',
    'skin_source':'Actual Rampage FBX skin influence profile, remapped by anatomical arm arclength',
    'authored_weight_vertices':int(region.sum()),'geometry_preserved':True,'bone_count':len(arm.bones),
    'game_triangles':len(mesh.data.polygons),'reference_adaptations':['Single large right arm; three support chains planted',
        'Neutral-pose alignment fades during the actual source strike','Torso/clavicle motion scaled for target proportions',
        'Palm-floor contact and target elbow limits','Two source clips joined and timed to existing damage windows'],
    'paths':paths,'preview_rendered':False,'runtime_tested':False},indent=2))
print('RAMPAGE_V8_AUTHORED_AND_EXPORTED',flush=True)
