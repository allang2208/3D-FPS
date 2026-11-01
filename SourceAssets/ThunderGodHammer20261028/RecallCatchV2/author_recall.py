"""Right-palm recall, weighted catch and delayed left-hand support on the native rig."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;R=P.parents[2];P.mkdir(exist_ok=True)
source=R/'SourceAssets/ThunderGodHammer20261028/ThunderThrowV1/author_motion.py'
# Reuse the source rig/contacts/solver without reauthoring the throw or its exports.
tree=ast.parse(source.read_text(encoding='utf-8'));prefix=[]
for n in tree.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='charge' for t in n.targets):break
    prefix.append(n)
scope={'__file__':str(source)};exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),scope)
env=scope['env'];rig=scope['rig'];idle=scope['idle'];rest=scope['rest'];local_rest=scope['local_rest'];grips=scope['grips']
env['OUT']=P/'Export';env['OUT'].mkdir(exist_ok=True)
blend=scope['blend'];ease=scope['ease'];FPS=240;READY=.32;CATCH=.60
idle_grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
receive_grips={s:scope['rolled_grip'](s,75. if s=='r' else 60.) for s in ('l','r')}
# The awaiting right palm remains just inside a slightly bent arm's reach.
# The shaft arrives upright, on the right side of the sightline.
receive=scope['weapon']((.19,.43,-.13),(0,-.10,.995))
for _ in range(20):
    hand=(receive@receive_grips['r']).translation;shoulder=idle['upperarm_r'].translation;v=hand-shoulder
    reach=((rest['lowerarm_r'].translation-rest['upperarm_r'].translation).length+(rest['hand_r'].translation-rest['lowerarm_r'].translation).length)*.92
    if v.length<=reach:break
    receive.translation-=v.normalized()*(v.length-reach)
lower=idle['WPN_root'].copy();lower.translation+=Vector((0,-.06,-.22))
start=scope['pose'](lower,{},.78)
left_rest=start['hand_l'].copy();left_rest.translation+=Vector((-.03,-.025,-.015))
def fingers(out,opening):
    locals_={b.name:out[b.parent.name].inverted()@out[b.name] if b.parent else out[b.name] for b in rig.data.bones}
    for b in rig.data.bones:
        if b.name.startswith(('thumb','index','middle','ring','pinky')):
            side=b.name[-1];locals_[b.name]=blend(locals_[b.name],local_rest[b.name],opening[side])
    for b in rig.data.bones:out[b.name]=out[b.parent.name]@locals_[b.name] if b.parent else locals_[b.name]
def pose(wpn,right,left,opening,state,idle_elbow=0.):
    out=copy.deepcopy(idle)
    for side,hand in (('r',right),('l',left)):
        scope['solve_native_arm'](out,side,hand,state,idle_elbow)
    out['WPN_root']=wpn;fingers(out,opening);return out
ready=[];state={}
for i in range(round(READY*FPS)+1):
    w=ease(i/FPS/READY)
    ready.append(pose(blend(lower,receive,w),blend(start['hand_r'],receive@receive_grips['r'],w),
                      blend(start['hand_l'],left_rest,w),{'r':.78,'l':.78+(.65-.78)*w},state))
ready[0]=copy.deepcopy(start)
catch=[];state={};recoil=receive.copy();recoil.translation+=Vector((0,-.065,-.025))
for i in range(round(CATCH*FPS)+1):
    t=i/FPS
    if t<=.10:wpn=receive
    elif t<=.20:wpn=blend(receive,recoil,ease((t-.10)/.10))
    else:wpn=blend(recoil,idle['WPN_root'],ease((t-.20)/.40))
    rg=env['blend_grasp'](receive_grips['r'],idle_grips['r'],ease((t-.20)/.40))
    lg=env['blend_grasp'](receive_grips['l'],idle_grips['l'],ease((t-.20)/.40))
    left=blend(left_rest,wpn@lg,ease((t-.14)/.22))
    catch.append(pose(wpn,wpn@rg,left,{'r':.78*(1-ease(t/.09)),'l':.65*(1-ease((t-.29)/.10))},state,ease((t-.20)/.40)))
catch[0]=copy.deepcopy(ready[-1]);catch[-1]=copy.deepcopy(idle)
for name,poses in [('A_ThunderHammer_RecallReady_V2',ready),('A_ThunderHammer_Catch_V2',catch)]:env['bake'](name,poses,FPS)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThunderHammer_RecallCatch_Editable.blend'))
(P/'motion.json').write_text(json.dumps({'fps':FPS,'ready_seconds':READY,'catch_seconds':CATCH,'closed_palm_seconds':.09,
    'hold_until':.10,'left_contact_seconds':.36,'clips':['A_ThunderHammer_RecallReady_V2','A_ThunderHammer_Catch_V2'],
    'source':str(source),'tested':False,'rendered':False},indent=2),encoding='utf-8')
print('THUNDER_RECALL_CATCH_AUTHORED')
