"""Inspect native hinge solutions for the reported left-arm pose."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
p=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(p.parent/'QuickCombatReachV6/Warhammer_QuickCombat_ReachV6_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def twist(q,axis):
    a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (a+math.pi)%(2*math.pi)-math.pi
u0=rest['lowerarm_l'].translation-rest['upperarm_l'].translation
l0=rest['hand_l'].translation-rest['lowerarm_l'].translation
n0=u0.cross(l0).normalized();L1=u0.length;L2=l0.length
scene.frame_set(0);idle={b.name:b.matrix.copy() for b in rig.pose.bones}
grip=idle['WPN_root'].inverted()@idle['hand_l']
print('NATIVE',math.degrees(u0.angle(l0)),L1,L2)
rows=[]
for t in (0,.03,.06,.09,.12,.15,.175,.20,.25,.33,.4):
    f=t*300;scene.frame_set(int(f),subframe=f-int(f));ref={b.name:b.matrix.copy() for b in rig.pose.bones}
    align=max(0,min(1,t/.09));align=align*align*(3-2*align)
    finish=max(0,min(1,(t-.33)/.17));finish=finish*finish*(3-2*finish);align*=1-finish
    best=None;fixed=None;roll_choices=[]
    for roll in [127]+list(range(-180,181,15)):
        target=ref['WPN_root']@Quaternion((0,0,1),math.radians(roll)*align).to_matrix().to_4x4()@grip
        s=ref['upperarm_l'].translation;h=target.translation;reach=h-s
        if reach.length>(L1+L2)*.96:continue
        axis=reach.normalized();d=reach.length;x=(L1*L1-L2*L2+d*d)/(2*d);c=s+axis*x
        r=math.sqrt(max(0,L1*L1-x*x));guide=ref['lowerarm_l'].translation-c;guide-=axis*guide.dot(axis);guide.normalize()
        dh=target.to_quaternion()@rest['hand_l'].to_quaternion().inverted()
        roll_best=None
        for degrees in range(-180,181,3):
            e=c+(Quaternion(axis,math.radians(degrees))@guide)*r;u=e-s;fore=h-e;normal=u.cross(fore).normalized()
            du=frame(u,normal)@frame(u0,n0).inverted();df=frame(fore,normal)@frame(l0,n0).inverted()
            needed=math.degrees(twist(dh@df.inverted(),fore.normalized()));bend=math.degrees(fore.angle(dh@l0))
            upper_delta=math.degrees((du@rest['upperarm_l'].to_quaternion()).rotation_difference(ref['upperarm_l'].to_quaternion()).angle)
            upper_delta=min(upper_delta,360-upper_delta)
            score=bend*bend+.8*max(0,abs(needed)-85)**2+.01*degrees*degrees+.015*(roll-127)**2+.01*upper_delta*upper_delta
            item={'time':t,'roll':roll,'pole':degrees,'bend':round(bend,2),'twist':round(needed,2),'upper_delta':round(upper_delta,2),'score':round(score,2)}
            if best is None or score<best['score']:best=item
            if roll==127 and (fixed is None or score<fixed['score']):fixed=item
            if roll_best is None or score<roll_best['score']:roll_best=item
        if t==.15 and roll in (127,-180,-90,0,90,180):
            print('CONTACT_ROLL',roll,'wrist',list(h),'hand_axis',list((dh@l0).normalized()),roll_best)
    rows.append({'time':t,'fixed_grip':fixed,'free_roll':best});print('CANDIDATE',rows[-1])
(p/'native_hinge_candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
