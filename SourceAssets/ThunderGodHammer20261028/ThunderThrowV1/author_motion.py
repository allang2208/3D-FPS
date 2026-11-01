"""Native two-hand overhead throw and catch on the existing hammer arm rig."""
import ast, copy, json, math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

DEST = Path(__file__).resolve().parent
PROJECT = DEST.parents[2]
source_path = PROJECT/'SourceAssets/SteelWarhammer20261014/HeavySlamV4/author_heavy.py'
# Reuse the accepted native rig, whole-hand contacts, helper bones and baking
# functions. Do not run the source's ground-slam authoring/exports.
tree = ast.parse(source_path.read_text(encoding='utf-8'))
prefix = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'grasp_recipe' for t in node.targets):
        break
    prefix.append(node)
env = {'__file__':str(source_path)}
exec(compile(ast.Module(body=prefix, type_ignores=[]), str(source_path), 'exec'), env)
rig, scene, rest, local_rest, idle = [env[k] for k in ('rig','scene','rest','local_rest','idle')]
env['OUT'] = DEST/'Export';env['OUT'].mkdir(parents=True,exist_ok=True)
FPS=240;RELEASE=.24;DURATION=.86;CATCH=.38
grips=env['grips'];idle_grips=env['idle_grips'];pivot=Vector((0,0,.19))
def weapon(center,axis):
    z=Vector(axis).normalized();x=Vector((1,0,0));y=z.cross(x).normalized()
    q=Matrix((x,y,z)).transposed().to_quaternion()
    return Matrix.LocRotScale(Vector(center)-q@pivot,q,Vector((1,1,1)))
top=weapon((0,.24,.22),(0,-.18,.984))
front=weapon((0,.43,-.10),(0,.94,-.342))
def blend(a,b,w):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,w),a.to_quaternion().slerp(b.to_quaternion(),w),Vector((1,1,1)))
def ease(x):
    x=max(0,min(1,x));return x*x*(3-2*x)

def rolled_grip(side,degrees):
    return Quaternion((0,0,1),math.radians(degrees)).to_matrix().to_4x4()@grips[side]
base_poles=copy.deepcopy(env['CFG']['elbow_pole_top'])
def solve_native_arm(out,side,hand,state,idle_elbow=0.):
    shoulder=idle['upperarm_'+side].translation
    axis=(hand.translation-shoulder).normalized()
    upper=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length
    fore=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
    distance=(hand.translation-shoulder).length
    center=shoulder+axis*((upper*upper-fore*fore+distance*distance)/(2*distance))
    neutral=hand.to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
    ideal=hand.translation-neutral*fore-center
    guide=(ideal-axis*ideal.dot(axis)).normalized()
    if idle_elbow:
        upper=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length
        fore=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
        distance=(hand.translation-shoulder).length
        center=shoulder+axis*((upper*upper-fore*fore+distance*distance)/(2*distance))
        target=idle['lowerarm_'+side].translation-center
        target=(target-axis*target.dot(axis)).normalized()
        angle=env['unwrap'](math.atan2(axis.dot(guide.cross(target)),guide.dot(target)),state.get(side+'_idle_plane_angle'))
        state[side+'_idle_plane_angle']=angle
        guide=Quaternion(axis,angle*idle_elbow)@guide
    pole=[guide.x*(1 if side=='r' else -1),guide.y,guide.z]
    env['CFG']['elbow_pole_top'][side]=pole;env['CFG']['elbow_pole_impact'][side]=pole
    env['SHOULDER_OVERRIDES'][side]=shoulder
    env['solve_arm'](out,side,hand,0.,0.,0.,state)

def pose(wpn,state,opening=0,idle_elbow=0.,rolls=None):
    wpn=wpn.copy();out=copy.deepcopy(idle)
    contacts={s:env['blend_grasp'](rolled_grip(s,(rolls or {}).get(s,0.)),idle_grips[s],idle_elbow) for s in ('l','r')}
    # Move the held assembly as one piece to stay inside both native arm reaches.
    for _ in range(16):
        correction=Vector()
        for side in ('l','r'):
            shoulder=idle['upperarm_'+side].translation
            reach=(wpn@contacts[side]).translation-shoulder
            length=((rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length+
                    (rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length)*.975
            if reach.length>length:correction-=reach.normalized()*(reach.length-length)*.55
        wpn.translation+=correction
    for side in ('l','r'):
        solve_native_arm(out,side,wpn@contacts[side],state,idle_elbow)
    out['WPN_root']=wpn
    if opening:
        locals_={b.name:out[b.parent.name].inverted()@out[b.name] if b.parent else out[b.name] for b in rig.data.bones}
        for b in rig.data.bones:
            if b.name.startswith(('thumb','index','middle','ring','pinky')):
                locals_[b.name]=blend(locals_[b.name],local_rest[b.name],opening)
        for b in rig.data.bones:out[b.name]=out[b.parent.name]@locals_[b.name] if b.parent else locals_[b.name]
    return out
top_rolls={'r':75.,'l':60.};front_rolls={'r':165.,'l':45.}
state={};charged=pose(top,state,rolls=top_rolls);top=charged['WPN_root'];state={};forward=pose(front,state,rolls=front_rolls);front=forward['WPN_root']
charge=[];state={}
for i in range(2*FPS+1):
    charge.append(pose(blend(idle['WPN_root'],top,ease(i/FPS/1.3)),state,idle_elbow=1-ease(i/FPS/1.3),rolls=top_rolls))
charge[0]=copy.deepcopy(idle);charge[-1]=copy.deepcopy(charged)
release=[];state={}
lower=idle['WPN_root'].copy();lower.translation+=Vector((0,-.06,-.22))
for i in range(round(DURATION*FPS)+1):
    t=i/FPS
    if t<=RELEASE:wpn=blend(top,front,ease(t/RELEASE)**1.35)
    elif t<.36:wpn=front
    else:wpn=blend(front,lower,ease((t-.36)/(DURATION-.36)))
    w=ease(t/RELEASE);recover=1-ease((t-.36)/(DURATION-.36))
    rolls={s:(top_rolls[s]+(front_rolls[s]-top_rolls[s])*w)*recover for s in ('l','r')}
    release.append(pose(wpn,state,.78*ease((t-RELEASE)/.07),rolls=rolls))
release[0]=copy.deepcopy(charged)
catch=[];state={}
for i in range(round(CATCH*FPS)+1):
    t=i/FPS;catch.append(pose(blend(front,idle['WPN_root'],ease(t/CATCH)),state,.78*(1-ease(t/.10))))
catch[-1]=copy.deepcopy(idle)
for name,poses in [('A_ThunderHammer_ThrowCharge',charge),('A_ThunderHammer_ThrowRelease',release),('A_ThunderHammer_Catch',catch)]:
    env['bake'](name,poses,FPS)
com=front@Vector((0,0,.70))
# FBX axis conversion followed by the tool viewmodel's yaw +90: author Y is forward.
offset=[com.y*100,com.x*100,com.z*100]
(DEST/'motion.json').write_text(json.dumps({'fps':FPS,'charge_seconds':2,'release_contact':RELEASE,'release_seconds':DURATION,
    'catch_seconds':CATCH,'launch_offset_cm':offset,'source_rig':str(source_path),
    'clips':['A_ThunderHammer_ThrowCharge','A_ThunderHammer_ThrowRelease','A_ThunderHammer_Catch'],
    'tested':False,'rendered':False},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(DEST/'ThunderHammer_Throw_Editable.blend'))
print('THUNDER_THROW_MOTION_SAVED',json.dumps(offset))
