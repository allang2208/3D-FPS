"""Rebuild the M870 support arm around an underhand pump grip.

Uses the existing skin/bind, source gun/right-hand/cartridge tracks and event
clock. The complete left arm, wrist and forearm skin stations are authored
together. No screenshots, rendering or gameplay validation are performed.
"""
import bpy,json,math,ast
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;P=O.parents[1];BASE=O.parent/'M870Tactical20261015';UC=O.parent/'M870UrbanAnimations20261015'
X=O/'Exports';(X/'Animations').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(UC/'M870_Urban_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;I=Matrix.Identity(4)
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
def under(n,root):
    while n:
        if n==root:return True
        n=parents.get(n)
    return False
def at(action,f):
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    s.frame_set(f)
    return {b.name:b.matrix.copy() for b in r.pose.bones}
idle=at(bpy.data.actions['A_M870_idle'],0)
canonical=rest['WPN_root']@idle['WPN_root'].inverted()
to_scene=canonical.inverted()
handbones=[n for n in rest if under(n,'hand_l')]
pumpcentre=Vector((0,.23,-.7594))
# The palm formerly lay across the top of the fore-end. Turn its complete
# grasp around the pump's longitudinal axis; fingers retain their joint shape.
grip_rotation=Matrix.Translation(pumpcentre)@Matrix.Rotation(-math.pi/2,4,'Y')@Matrix.Translation(-pumpcentre)
grip={n:grip_rotation@canonical@idle[n] for n in handbones}
pump_inverse=rest['WPN_bolt'].inverted()
grip_in_pump={n:pump_inverse@m for n,m in grip.items()}
shoulder_anchor=to_scene@Vector((-.20,-.115,-.940))
outward=to_scene.to_3x3()@Vector((-1.,-.2,-1.))
u0=rest['lowerarm_l'].translation-rest['upperarm_l'].translation
f0=rest['hand_l'].translation-rest['lowerarm_l'].translation
l1=u0.length;l2=f0.length
h0=u0.cross(f0).normalized()
def basis(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized()
    return Matrix((x,z.cross(x),z)).transposed()
fu0=basis(u0,h0);fl0=basis(f0,h0)
def signed_twist(q,axis):
    q.normalize();axis=axis.normalized()
    angle=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (angle+math.pi)%(2*math.pi)-math.pi
def posed(restname,position,deformation):
    return Matrix.LocRotScale(position,deformation@rest[restname].to_quaternion(),Vector((1,1,1)))
def solve(row,elbow_angle=None):
    gun_carry=canonical@row['WPN_root']@rest['WPN_root'].inverted()
    roll=signed_twist(gun_carry.to_quaternion(),Vector((0,1,0)))
    # UC turns the loading port upward by roughly 150 degrees. A welded
    # underhand grip would twist the arm with the receiver. Let the round
    # fore-end roll within the support hand while the palm stays underneath.
    counterroll=Matrix.Translation(pumpcentre)@Matrix.Rotation(-roll,4,'Y')@Matrix.Translation(-pumpcentre)
    for n in handbones:row[n]=row['WPN_bolt']@pump_inverse@counterroll@grip[n]
    hand=row['hand_l'];w=hand.translation
    # Preserve subtle body carry while preventing the old raised shoulder
    # from sweeping its sleeve across the rear sight during ADS.
    a=shoulder_anchor+(row['upperarm_l'].translation-idle['upperarm_l'].translation)*.20
    axis=w-a;distance=axis.length;maxreach=.94*(l1+l2)
    if distance>maxreach:a+=axis.normalized()*(distance-maxreach);axis=w-a;distance=axis.length
    axis.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*max(distance,1.e-8))
    center=a+axis*along;radius=math.sqrt(max(0,l1*l1-along*along))
    dh=hand.to_quaternion()@rest['hand_l'].to_quaternion().inverted()
    ideal=w-dh@f0
    fingerpole=ideal-center;fingerpole-=axis*fingerpole.dot(axis)
    basepole=outward-axis*outward.dot(axis)
    if fingerpole.length<1.e-7:fingerpole=basepole.copy()
    pole=(fingerpole.normalized()*.70+basepole.normalized()*.30).normalized()
    def candidate(angle):
        e=center+Quaternion(axis,angle)@pole*radius;u=e-a;f=w-e;hinge=u.cross(f).normalized()
        dl=(basis(f,hinge)@fl0.inverted()).to_quaternion()
        tau=signed_twist(dl.inverted()@dh,f0)
        # Use the same pronation branch throughout the source's canted
        # reload. Crossing +180/-180 must not flip the skin station roll.
        reference=math.radians(-85)
        tau+=2*math.pi*round((reference-tau)/(2*math.pi))
        wrist=(dh@f0).angle(f)
        return e,u,f,dl,tau,wrist
    if elbow_angle is None:
        best=None
        for degree in range(-135,136,3):
            angle=math.radians(degree);e,u,f,dl,tau,wrist=candidate(angle)
            ce=canonical@e
            overload=max(0,abs(tau)-math.radians(100))
            across=max(0,ce.x+.025);raised=max(0,ce.z+.805)
            score=wrist*wrist+4*overload*overload+.025*angle*angle+80*(across*across+raised*raised)
            if best is None or score<best[0]:best=(score,angle)
        elbow_angle=best[1]
    e,u,f,dl,tau,wrist=candidate(elbow_angle)
    fore=max(-math.radians(105),min(math.radians(105),tau));remainder=tau-fore
    fe=Quaternion(f.normalized(),remainder)@dl
    du=(fe@u0).rotation_difference(u)@fe
    row['clavicle_l']=idle['clavicle_l'].copy();row['clavicle_l'].translation+=a-idle['upperarm_l'].translation
    row['upperarm_l']=posed('upperarm_l',a,du)
    row['lowerarm_l']=posed('lowerarm_l',e,fe)
    # Helpers are siblings, not a twist chain. Reconstruct each skin station
    # from its own bind, rather than retaining donor rotations after IK.
    for n in ('lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l'):
        base=rest[n].translation-rest['lowerarm_l'].translation
        station=base.dot(f0)/f0.length_squared
        off=base-f0*station
        share=max(0,min(1,station))
        q=Quaternion(f.normalized(),fore*share)@fe
        row[n]=posed(n,e+f*station+q@off,q)
    # These rigs presently have no upper-arm helpers, but preserve native
    # children of the upper arm if the retained bind gains any later.
    for n in rest:
        if n.startswith('upperarm_twist_') and n.endswith('_l'):
            base=rest[n].translation-rest['upperarm_l'].translation
            station=base.dot(u0)/u0.length_squared;off=base-u0*station
            row[n]=posed(n,a+u*station+du@off,du)
    # Real rear aperture centre and front post tip, measured in the source
    # mesh; the same marker tracks drive the existing ADS calibration.
    gm=row['WPN_root']@rest['WPN_root'].inverted()
    for n,p in [('WPN_RearSight',(0,-.0820095082,-.7019031198)),('WPN_FrontSight',(0,.4493982,-.703346488))]:
        marker=rest[n].copy();marker.translation=Vector(p);row[n]=gm@marker
    return dict(elbow_angle=elbow_angle,wrist_bend_deg=math.degrees(wrist),forearm_pronation_deg=math.degrees(fore),upper_roll_deg=math.degrees(remainder))

tree=ast.parse((BASE/'author_m870.py').read_text())
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('select','bake')]
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
authored={};exec(compile(ast.Module(body=selected,type_ignores=[]),str(BASE/'author_m870.py'),'exec'))
source_roles={k:v['action'] for k,v in json.loads((BASE/'authoring.json').read_text())['clips'].items()}
source_roles.update({k:v['action'] for k,v in json.loads((UC/'authoring.json').read_text())['clips'].items()})
# Resolve actions before creating new names with Blender's numeric suffixes.
source_actions={role:bpy.data.actions[name] for role,name in source_roles.items()}
recipe={}
for role,action in source_actions.items():
    frames=int(round(action.frame_range[1]))+1
    inputs=[];angles=[]
    for frame in range(frames):
        row=at(action,frame);inputs.append(row)
        angles.append(solve({n:m.copy() for n,m in row.items()})['elbow_angle'])
    # Smooth the construction parameter, then solve again on the exact
    # bone-length circle. Pin clip endpoints to keep transitions identical.
    smooth=[]
    for i in range(frames):
        weights=[(j,math.exp(-.5*((j-i)/2.5)**2)) for j in range(max(0,i-7),min(frames,i+8))]
        value=sum(angles[j]*w for j,w in weights)/sum(w for _,w in weights)
        edge=min(1.,i/7.,(frames-1-i)/7.)
        smooth.append(angles[i]*(1-edge)+value*edge)
    rows=[];stages=[]
    for frame,row in enumerate(inputs):
        data=solve(row,smooth[frame]);rows.append(row)
        if frame in (0,frames//2,frames-1):stages.append(dict(frame=frame,**data))
    bake(role,rows);recipe[role]=dict(input_action=action.name,frames=frames,arm_recipe=stages)
    print('M870_GRIP_AUTHORED',role,frames,flush=True)
new_idle=bpy.data.actions[authored['idle']['action']]
r.animation_data.action=new_idle;r.animation_data.action_slot=new_idle.slots[0];s.frame_set(0)
s.frame_start=0;s.frame_end=179;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_GripADS_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(dict(clips=authored,recipe=recipe,grip_roll_degrees=-90,pump_axis=list(pumpcentre),left_shoulder_canonical=[-.20,-.115,-.940],native_upperarm_length=l1,native_forearm_length=l2,scope='all 13 active M870 roles including shared ADS idle and fire',runtime_tested=False,visual_tested=False),indent=2))
print('M870_GRIP_COMPLETE',len(authored),'clips',flush=True)
