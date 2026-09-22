"""Short forward toss: fixed limb lengths, shoulder lead, wrist/finger follow-through.
Preserves the existing 1.5 s clip / 0.75 s release and every other animation.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');FPS=60
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Idle.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(1)
base={b.name:b.matrix_basis.copy() for b in r.pose.bones};root=r.matrix_world.copy()
worldbase={b.name:root@b.matrix for b in r.pose.bones}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');r.animation_data_clear();r.data.pose_position='POSE'
s=bpy.context.scene;s.render.fps=FPS;s.frame_start=1;s.frame_end=91
def update():bpy.context.view_layer.update()
def world(n):return r.matrix_world@r.pose.bones[n].matrix
def put(n,m):r.pose.bones[n].matrix=r.matrix_world.inverted()@m;update()
def rotate(n,q):
    m=world(n);p=m.translation.copy();m=q.to_matrix().to_4x4()@m;m.translation=p;put(n,m)
def smooth(t):t=max(0.,min(1.,t));return t*t*(3-2*t)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def arc(t,keys):
    for j in range(len(keys)-1):
        ta,a=keys[j];tb,b=keys[j+1]
        if ta<=t<=tb:
            u=(t-ta)/(tb-ta);a=Vector(a);b=Vector(b)
            ma=Vector((0,0,0)) if j==0 else (b-Vector(keys[j-1][1]))/(tb-keys[j-1][0])
            mb=Vector((0,0,0)) if j+2==len(keys) else (Vector(keys[j+2][1])-a)/(keys[j+2][0]-ta)
            return a*(2*u**3-3*u*u+1)+ma*(tb-ta)*(u**3-2*u*u+u)+b*(-2*u**3+3*u*u)+mb*(tb-ta)*(u**3-u*u)
    return Vector(keys[-1][1])
def solve(upper,lower,end,target,pole):
    a,b,c=[world(n) for n in (upper,lower,end)];p=a.translation
    l1=(b.translation-p).length;l2=(c.translation-b.translation).length
    direction=(target-p).normalized();length=max(abs(l1-l2)+.006,min((target-p).length,(l1+l2)*.97))
    target=p+direction*length;knee=pole-p;knee-=direction*knee.dot(direction);knee.normalize()
    along=(l1*l1-l2*l2+length*length)/(2*length)
    elbow=p+direction*along+knee*math.sqrt(max(0,l1*l1-along*along))
    rotate(upper,(b.translation-p).rotation_difference(elbow-p))
    b=world(lower);c=world(end);rotate(lower,(c.translation-b.translation).rotation_difference(target-b.translation))
    # End position remains the bone-chain result. Never translate the hand away
    # from its forearm to satisfy an unreachable source-model trajectory.

keys=[(0,(0,0,0)),(.18,(-.014,.025,.045)),(.40,(-.026,.018,.16)),
      (.58,(.014,-.075,.24)),(.75,(.09,-.285,.31)),(.85,(.115,-.35,.285)),
      (1.04,(.07,-.24,.16)),(1.28,(.016,-.06,.035)),(1.5,(0,0,0))]
samples=[];feet={side:[] for side in ('l','r')};opening=[]
for i in range(91):
    t=i/FPS;s.frame_set(i+1);r.matrix_world=root
    for b in r.pose.bones:b.rotation_mode='QUATERNION';b.matrix_basis=base[b.name]
    update()
    effort=ramp(t,.25,.75)*(1-ramp(t,.9,1.5));prep=ramp(t,.05,.32)*(1-ramp(t,.36,.65))
    m=world('pelvis');m.translation+=Vector((.012*effort-.006*prep,-.019*effort+.009*prep,-.010*effort));put('pelvis',m)
    for n,amount in [('spine_01',.20),('spine_03',.35),('spine_05',.45)]:
        rotate(n,Quaternion((0,0,1),math.radians(-10*effort+4*prep)*amount))
        rotate(n,Quaternion((1,0,0),math.radians(6*effort-2.5*prep)*amount))
    rotate('clavicle_r',Quaternion((0,0,1),math.radians(-3)*effort))
    target=worldbase['hand_r'].translation+arc(t,keys)
    pole=worldbase['lowerarm_r'].translation+Vector((-.055,-.035,.025))*effort+Vector((-.02,.04,.015))*prep
    solve('upperarm_r','lowerarm_r','hand_r',target,pole)
    # Small wrist follow-through; the upper arm and forearm supply the throw.
    follow=ramp(t,.70,.85)*(1-ramp(t,.96,1.42))
    wrist=9*prep-15*follow
    transverse=(world('index_01_r').translation-world('pinky_01_r').translation).normalized()
    rotate('hand_r',Quaternion(transverse,math.radians(wrist)))
    forearm=(world('hand_r').translation-world('lowerarm_r').translation).normalized()
    rotate('hand_r',Quaternion(forearm,math.radians(-5*prep+9*follow)))
    for side in ('l','r'):
        solve('thigh_'+side,'calf_'+side,'foot_'+side,worldbase['foot_'+side].translation,worldbase['calf_'+side].translation)
        m=world('foot_'+side);loc=m.translation.copy();m=worldbase['foot_'+side].copy();m.translation=loc;put('foot_'+side,m)
    # Keep the staff arm steady through the small torso shift.
    solve('upperarm_l','lowerarm_l','hand_l',worldbase['hand_l'].translation,worldbase['lowerarm_l'].translation)
    m=worldbase['hand_l'].copy();m.translation=world('hand_l').translation;put('hand_l',m)
    for finger,offset,amount in [('index',-.008,.91),('middle',0,.87),('ring',.012,.78),('pinky',.024,.70),('thumb',-.022,.72)]:
        release=ramp(t,.712+offset,.790+offset)*(1-ramp(t,1.09+offset,1.44+offset))
        for segment in ('01','02','03'):
            b=r.pose.bones[finger+'_'+segment+'_r'];loc,q,scale=base[b.name].decompose()
            b.matrix_basis=Matrix.LocRotScale(loc,q.slerp(Quaternion(),release*amount),scale)
    update()
    for side in ('l','r'):
        put('ik_foot_'+side,world('foot_'+side));put('ik_hand_'+side,world('hand_'+side));feet[side].append(world('ball_'+side).translation.copy())
    for b in r.pose.bones:
        b.keyframe_insert('location',frame=i+1);b.keyframe_insert('rotation_quaternion',frame=i+1);b.keyframe_insert('scale',frame=i+1)
    for channel in ('location','rotation_euler','scale'):r.keyframe_insert(channel,frame=i+1)
    opening.append(ramp(t,.712,.790)*(1-ramp(t,1.09,1.44)))
    samples.append({'time':t,'shoulder':list(world('upperarm_r').translation),'elbow':list(world('lowerarm_r').translation),'hand':list(world('hand_r').translation)})
r.animation_data.action.name='A_WitchRebuilt_ThrowPoisonBottle';s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_ThrowPoisonBottle.blend'))
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
file=ROOT/'Delivery/A_WitchRebuilt_ThrowPoisonBottle.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
    use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,
    bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
manifest=json.loads((ROOT/'Authoring/motion_manifest.json').read_text());curves={'GripOpen_r':opening}
for side,points in feet.items():curves['FootSpeed_'+side]=[(points[min(90,i+1)]-points[max(0,i-1)]).length*100*FPS/max(1,min(90,i+1)-max(0,i-1)) for i in range(91)]
manifest['ThrowPoisonBottle']={'file':str(file),'fps':FPS,'frames':91,'duration':1.5,'loop':False,'release':.75,
    'source':'Authored short forward toss guided by original attacking-2; fixed anatomical segment lengths, shoulder lead, staggered finger release',
    'curves':curves}
(ROOT/'Authoring/motion_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT/'Refinement20260922/throw_motion.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
print('Authored only ThrowPoisonBottle: 60 fps, 1.5 s, release 0.75 s')
