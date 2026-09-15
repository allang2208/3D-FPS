"""Author the single-wield extractor press with a canted palm and whole-arm support.

The surface/arm fit below is part of making the pose, not an acceptance run.
No renders, runtime tests, or changes to the weapon's mechanical clock.
"""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

_clearance_dir=Path(__file__).resolve().parent
_basis_file=_clearance_dir/'reference_basis.py'
__file__=str(_basis_file)
exec(compile(_basis_file.read_text(encoding='utf-8'),str(_basis_file),'exec'),globals())
O=_clearance_dir;__file__=str(O/'author_actions.py');(O/'Animations').mkdir(exist_ok=True)

def array(m):return np.asarray(m,dtype=np.float64)

# Skin all finger surfaces in the actual FK hand shape, including the thumb
# base, webbing, fingertips and glove back. Add triangle centroids/edge points
# so a broad face cannot straddle a thin part between its vertices.
shape_pose={n:m.copy() for n,m in rest.items()}
shape_pose['hand_l']=Matrix.Identity(4)
for n in finger_names:shape_pose[n]=donor_shape[n]
hand_skin=[]
for obj in bpy.data.objects:
    if obj.type!='MESH' or not obj.vertex_groups.get('hand_l'):continue
    group_names={g.index:g.name for g in obj.vertex_groups}
    transform=rig.matrix_world.inverted()@obj.matrix_world
    points=[];valid=[]
    for v in obj.data.vertices:
        co=transform@v.co;point=Vector();total=0.;hand_weight=0.
        for group in v.groups:
            name=group_names[group.group]
            if name not in rest:continue
            is_hand=name=='hand_l' or name in finger_names
            if is_hand:hand_weight+=group.weight
            # Wrist seam follows the neutral extension of the same hand frame.
            M=shape_pose[name] if is_hand else rest['hand_l'].inverted()@rest[name]
            point+=(M@rest[name].inverted()@co)*group.weight;total+=group.weight
        points.append(point/max(total,1e-8));valid.append(hand_weight>.50)
    hand_skin.extend(points[i] for i,ok in enumerate(valid) if ok)
    obj.data.calc_loop_triangles()
    for tri in obj.data.loop_triangles:
        ids=list(tri.vertices)
        if not all(valid[i] for i in ids):continue
        a,b,c=(points[i] for i in ids)
        hand_skin.extend(((a+b+c)/3,(a+b)/2,(b+c)/2,(c+a)/2))
# Exact duplicate skin/edge points need not be evaluated twice during authoring.
hand_surface=np.unique(np.round(array(hand_skin),6),axis=0)
surface_forward=hand_surface@array(hand_forward)
surface_radial=hand_surface@array(radial)
surface_depth=hand_surface@array(palm)
palm_surface=hand_surface[(surface_forward>.015)&(surface_forward<.078)&(surface_depth>0)]

solid_parts=[part for part in geometry['parts'] if len(part['bones'])==1
             and part['bones'][0] in ('WPN_root','WPN_Cylinder','WPN_Crane','WPN_Trigger','WPN_Hammer')]
part_min=np.array([part['min'] for part in solid_parts]);part_max=np.array([part['max'] for part in solid_parts])
neutral_lower_in_hand=rest['hand_l'].to_quaternion().inverted()@rest['lowerarm_l'].to_quaternion()
neutral_forward=(rest['hand_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation)).normalized()
rest_upper_axis=rest['lowerarm_l'].translation-rest['upperarm_l'].translation
rest_lower_axis=rest['hand_l'].translation-rest['lowerarm_l'].translation
idle_axis=(idle['hand_l'].translation-source_shoulder).normalized()
idle_pole=idle['lowerarm_l'].translation-source_shoulder
idle_pole=(idle_pole-idle_axis*idle_pole.dot(idle_axis)).normalized()
rod_frame=peak_GD.to_quaternion()
previous_heading=Quaternion(reference_normal,math.radians(-85))@reference_forward
heading_local=rod_frame.inverted()@previous_heading

def hand_rotation(p,parameters):
    heading,tilt_side,tilt_forward=parameters[:3]
    rod_normal=Vector((0,1,0))
    direction=Quaternion(rod_normal,math.radians(heading))@heading_local
    side_axis=direction.cross(rod_normal).normalized()
    cant=Quaternion(direction,math.radians(tilt_side))@Quaternion(side_axis,math.radians(tilt_forward))
    normal=cant@rod_normal;direction=cant@direction
    q=Matrix((direction.cross(normal),direction,normal)).transposed().to_quaternion()@hand_frame.inverted()
    return (p['WPN_Crane']@gunlocal['WPN_Crane'].inverted()).to_quaternion()@q

def contact_patch(parameters):
    # Contact on a real, deformed palm point rather than an averaged plane.
    center=hand_forward*parameters[3]+radial*parameters[4]
    depth=palm_surface@array(palm)
    lateral=palm_surface-depth[:,None]*array(palm)-array(center)
    metric=np.sum(lateral*lateral,axis=1)-depth*.0005
    return Vector(palm_surface[int(np.argmin(metric))])

def press_target(p,parameters,contact,travel):
    D=p['WPN_Crane']@gunlocal['WPN_Crane'].inverted()
    normal=(D.to_3x3()@Vector((0,1,0))).normalized()
    q=hand_rotation(p,parameters)
    surface=D@(cap+Vector((0,travel,0)))-normal*.003
    return Matrix.LocRotScale(surface-q@contact,q,Vector((1,1,1)))

def support(H,old,weight):
    shoulder=old['upperarm_l'].translation.lerp(source_shoulder,weight)
    delta=H.translation-shoulder;distance=delta.length;axis=delta.normalized()
    reach=(upper_length+lower_length)*.94
    extension=max(0.,distance-reach)
    shoulder+=axis*extension;distance-=extension
    distance=max(abs(upper_length-lower_length)+.0001,distance)
    along=(upper_length**2-lower_length**2+distance**2)/(2*distance)
    center=shoulder+axis*along
    natural=H.to_quaternion()@neutral_forward
    wanted=H.translation-natural*lower_length
    neutral_pole=wanted-center;neutral_pole-=axis*neutral_pole.dot(axis)
    transported=idle_axis.rotation_difference(axis)@idle_pole
    pole=transported if neutral_pole.length<1e-5 else neutral_pole.normalized()
    old_pole=old['lowerarm_l'].translation-center;old_pole-=axis*old_pole.dot(axis)
    if old_pole.length>1e-5:
        pole=old_pole.normalized().rotation_difference(pole).slerp(Quaternion(),1-weight)@old_pole.normalized()
    elbow=center+pole.normalized()*math.sqrt(max(0,upper_length**2-along**2))
    return shoulder,elbow,natural,extension

def surface_cost(points,p,clearance=.006):
    total=0.
    for part,lo,hi in zip(solid_parts,part_min,part_max):
        bone=part['bones'][0]
        inverse=(p[bone]@gunlocal[bone].inverted()).inverted()
        M=array(inverse);local=points@M[:3,:3].T+M[:3,3]
        mid=(lo+hi)*.5;half=(hi-lo)*.5
        d=np.abs(local-mid)-half
        near=d[np.all(d<clearance,axis=1)]
        if len(near)==0:continue
        signed=np.linalg.norm(np.maximum(near,0),axis=1)+np.minimum(np.max(near,axis=1),0)
        violation=np.maximum(clearance-signed,0)
        # A local penetration cannot disappear in a mean across thousands of
        # clear vertices. Worst depth and affected surface both drive the fit.
        total+=float(np.max(violation)**2*3+np.sum(violation*violation)/len(points))*1e6
    return total

fit_samples=[]
for speed in (False,True):
    for t in (.77,.85,.94,1.03,1.08,1.16,1.22):
        p=_base_speed(0,t*3.85/3.6) if speed else _base_single(0,6,t)
        travel=(-.050 if t==.77 else stroke(t)-.050*ease((t-1.08)/.14))
        fit_samples.append((p,travel))

def fit_cost(parameters):
    contact=contact_patch(parameters);cost=0.
    for p,travel in fit_samples:
        H=press_target(p,parameters,contact,travel)
        M=array(H);points=hand_surface@M[:3,:3].T+M[:3,3]
        cost+=surface_cost(points,p)
        shoulder,elbow,natural,extension=support(H,p,1.)
        actual=(H.translation-elbow).normalized()
        bend=actual.angle(natural)
        cost+=bend*bend*90+max(0,bend-math.radians(24))**2*1800
        cost+=extension*extension*80000
        # Keep the left elbow to the player's left and below the wrist.
        cost+=max(0,.085-elbow.x)**2*25000+max(0,elbow.z-H.translation.z+.035)**2*20000
        arm_points=np.array([list(elbow.lerp(H.translation,t)) for t in (.12,.32,.52,.72,.88)])
        cost+=surface_cost(arm_points,p,.030)
    # Prefer a restrained cant and the centre/outboard heel; no unconstrained
    # finger solving and no forced 180-degree hand rotations.
    cost+=parameters[0]**2*.008+(parameters[1]**2+parameters[2]**2)*.014
    return cost/len(fit_samples)

print('PALM_CLEARANCE_AUTHORING_SURFACE',len(hand_surface),flush=True)
bounds=[(-70,70),(-35,35),(-35,35),(.025,.060),(-.032,.032)]
# Small deterministic bounded authoring search, using Blender's bundled numpy.
rng=np.random.default_rng(715);lo=np.array([b[0] for b in bounds]);hi=np.array([b[1] for b in bounds])
population=lo+rng.random((28,5))*(hi-lo);population[0]=[0,0,0,.046,0]
scores=np.array([fit_cost(row) for row in population])
for generation in range(28):
    for i in range(len(population)):
        choices=[j for j in range(len(population)) if j!=i]
        a,b,c=population[rng.choice(choices,3,replace=False)]
        proposal=np.clip(a+.7*(b-c),lo,hi)
        mask=rng.random(5)<.8;mask[int(rng.integers(5))]=True
        proposal=np.where(mask,proposal,population[i]);score=fit_cost(proposal)
        if score<scores[i]:population[i]=proposal;scores[i]=score
    print('PALM_CLEARANCE_FIT',generation+1,float(scores.min()),flush=True)
parameters=population[int(np.argmin(scores))].copy();best_cost=float(scores.min())
for fraction in (.035,.012,.004):
    step=(hi-lo)*fraction
    for _ in range(5):
        changed=False
        for axis in range(5):
            for sign in (-1,1):
                proposal=parameters.copy();proposal[axis]=np.clip(proposal[axis]+sign*step[axis],lo[axis],hi[axis])
                score=fit_cost(proposal)
                if score<best_cost:parameters=proposal;best_cost=score;changed=True
        if not changed:break
contact=contact_patch(parameters)
settings={'heading_delta_deg':float(parameters[0]),'palm_cant_deg':[float(v) for v in parameters[1:3]],
          'contact_skin_hand_m':list(contact),'contact_gap_m':.003,'solid_clearance_m':.006,
          'withdraw_m':.050,'hand_surface_points':len(hand_surface),
          'wrist':'neutral rest relationship; whole forearm follows hand with fixed segment lengths',
          'reference':'DonorPress20260915 donor phalanx shape; LeftRecovery mechanics',
          'testing':'Not performed; geometry constraints used only to author the action'}
print('PALM_CLEARANCE_AUTHORED_PARAMETERS',json.dumps(settings),flush=True)

def whole_arm(p,H,weight):
    old={n:m.copy() for n,m in p.items()}
    shoulder,elbow,_,_=support(H,old,weight)
    upper_axis=elbow-shoulder;lower_axis=H.translation-elbow
    upper_q=(old['lowerarm_l'].translation-old['upperarm_l'].translation).rotation_difference(upper_axis)@old['upperarm_l'].to_quaternion()
    natural_q=H.to_quaternion()@neutral_lower_in_hand
    natural_axis=natural_q@rest['lowerarm_l'].to_quaternion().inverted()@rest_lower_axis
    neutral_q=natural_axis.rotation_difference(lower_axis)@natural_q
    source_q=(old['hand_l'].translation-old['lowerarm_l'].translation).rotation_difference(lower_axis)@old['lowerarm_l'].to_quaternion()
    p['upperarm_l']=Matrix.LocRotScale(shoulder,upper_q,old['upperarm_l'].to_scale())
    p['lowerarm_l']=Matrix.LocRotScale(elbow,source_q.slerp(neutral_q,weight),old['lowerarm_l'].to_scale())
    p['clavicle_l']=old['clavicle_l'].copy();p['clavicle_l'].translation+=shoulder-old['upperarm_l'].translation
    for n in names:
        if n.endswith('_l') and n.startswith(('upperarm_twist','lowerarm_twist')):
            segment='upperarm_l' if n.startswith('upperarm') else 'lowerarm_l'
            p[n]=p[segment]@mix(old[segment].inverted()@old[n],rest[segment].inverted()@rest[n],weight)
    p['hand_l']=H.copy()
    if 'ik_hand_l' in p:p['ik_hand_l']=H.copy()

def clear_curve(A,B,w,depart=False):
    v=ease(w);H=mix(A,B,v)
    # Fixed component-space outer-left corridor, independent of gun banking.
    c1=A.translation+Vector((.105,.025,-.045 if depart else .035))
    c2=B.translation+Vector((.095,.010,-.040 if depart else .030))
    H.translation=A.translation*(1-v)**3+c1*3*v*(1-v)**2+c2*3*v*v*(1-v)+B.translation*v**3
    return H

entries={}
def apply_press(p,t,speed):
    finish=1.40 if speed else 1.50
    if t<=.40 or t>=finish:return p
    if speed not in entries:
        sample=(lambda u:_base_speed(0,u*3.85/3.6)) if speed else (lambda u:_base_single(0,6,u))
        entries[speed]=(sample(.40)['hand_l'].copy(),sample(finish)['hand_l'].copy())
    A,B=entries[speed];before=press_target(p,parameters,contact,-.050)
    if t<.77:
        w=ease((t-.40)/.37);H=clear_curve(A,before,(t-.40)/.37)
        shape=blend_shapes(relaxed,donor_shape,w)
    elif t<.85:
        H=press_target(p,parameters,contact,-.050*(1-ease((t-.77)/.08)));shape=donor_shape
    elif t<1.08:H=press_target(p,parameters,contact,stroke(t));shape=donor_shape
    elif t<1.22:
        H=press_target(p,parameters,contact,stroke(t)-.050*ease((t-1.08)/.14));shape=donor_shape
    else:
        w=(t-1.22)/(finish-1.22);H=clear_curve(before,B,w,True)
        shape=blend_shapes(donor_shape,templates['loader'] if speed else relaxed,ease(w))
    weight=ease((t-.40)/.37)*(1-ease((t-1.22)/(finish-1.22)))
    whole_arm(p,H,weight);apply_hand_shape(p,shape,1.)
    return p

def pose_single(start,count,t):
    p=_base_single(start,count,t)
    return apply_press(p,t,False) if start==0 else p

def pose_speed(start,t):
    p=_base_speed(start,t)
    return apply_press(p,t*3.6/3.85,True) if start==0 else p

if __name__=='__main__':
    bake_source='def bake('+previous.split('def bake(',1)[1].split('\nactions={}',1)[0]
    exec(compile(bake_source.replace('DW715_Flick_','DW715_PalmClearance_').replace('DW715_FLICK_EXPORTED','DW715_PALM_CLEARANCE_EXPORTED'),__file__,'exec'),globals())
    destination='/Game/Weapons/DanWesson715/PalmClearance20260915/Animations'
    manifest={'sample_rate':120,'adaptation':settings,'clips':{},'testing':'Not performed; user testing'};actions={}
    for count in range(1,7):
        kind=f'single_0_{count}';duration=EMPTY_BEGIN+count*STEP+TAIL
        actions[kind]=bake(kind,duration,lambda t,c=count:pose_single(0,c,t))
        manifest['clips'][kind]={'duration':duration,'destination':destination}
    actions['speed_0']=bake('speed_0',3.85,lambda t:pose_speed(0,t))
    manifest['clips']['speed_0']={'duration':3.85,'destination':destination}
    rig.animation_data.action=actions['single_0_6'];rig.animation_data.action_slot=actions['single_0_6'].slots[0]
    s.frame_start=0;s.frame_end=528;s.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_PalmClearance_Editable.blend'))
    (O/'animation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('DW715_PALM_CLEARANCE_AUTHORING_COMPLETE',flush=True)
