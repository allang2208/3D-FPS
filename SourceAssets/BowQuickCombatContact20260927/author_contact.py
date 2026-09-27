"""V4: fit the whole right grasp to the wider upper bow and its wrapping."""
from pathlib import Path
P=Path(__file__).parent
source=(P.parent/'BowQuickCombatPush20260927/generated_push_v3.py').read_text()
marker='idle_local = {n: idle[parent[n]].inverted() @ idle[n] if parent[n] else idle[n] for n in order}'
assert marker in source
source=source.replace(marker,'''# Surface-fitted complete right grasp; native rest, skin and bone lengths stay intact.
fit = json.loads((P/'contact-fit.json').read_text())
right_contact = Matrix(fit['right_contact'])
right_closed_local = {n:Matrix(m) for n,m in fit['right_closed_local'].items()}
'''+marker)
source=source.replace('Author the V7 bow\'s grab / down-left sweep / release, without rendering.',
    'Author the V7 bow upper grasp / horizontal forward push / release.')
source=source.replace('Small lift during the reach, visible right/up loading, fast diagonal sweep,',
    'Small lift during the reach, centre the horizontal bow, then drive forwards,')
source=source.replace('fitted to real upper-limb centreline; horizontal forward push',
    'surface-fitted palm and individual fingers around the upper wrapping; horizontal forward push')
marker='def pose(t):'
source=source.replace(marker,'''# Open the fitted grip for approach/release, instead of interpolating straight
# through the wood from the unrelated string-pulling finger pose.
right_open_local = {n:m.copy() for n,m in right_closed_local.items()}
for d in anatomy['r']['digits']:
    n=d['bone']; segment=d['segment']-1
    if n not in right_open_local: continue
    angle=(20.,10.,5.)[segment] if d['digit']=='thumb' else (-25.,-15.,-5.)[segment]
    axis=rest[parent[n]].to_3x3().inverted()@(R@Vector(d['across']))
    value=right_open_local[n]
    right_open_local[n]=mat(value.translation,Matrix.Rotation(math.radians(angle),3,axis)@value.to_3x3())

'''+marker)
start=source.index('    if t < G:');end=source.index("    targets = {'l':left,'r':right}",start)
source=source[:start]+'''    if t < G:
        target=right.translation
        outside=bow.to_3x3()@Vector((0.,1.,0.))
        p=hand_path([(0.,idle['hand_r'].translation),(.07,target+outside*10.),
                     (.105,target+outside*5.),(G,target)],t)
        right=mat(p,idle['hand_r'].to_quaternion().slerp(right.to_quaternion(),smooth(t/.075)).to_matrix())
    elif t > RELEASE:
        opening=smooth((t-RELEASE)/.075)
        peeled=right.copy();peeled.translation+=bow.to_3x3()@Vector((0.,10.*opening,0.))
        right=blend_frame(peeled,idle['hand_r'],smooth((t-RELEASE-.075)/(L-RELEASE-.075)))
    closed=smooth((t-.07)/(G-.07))*(1.-smooth((t-RELEASE)/.075))
    fingers_active=smooth(t/.055)*(1.-smooth((t-RELEASE-.075)/(L-RELEASE-.075)))
'''+source[end:]
old='''                        value = mat(value.translation, value.to_quaternion().slerp(
                            right_closed_local[n].to_quaternion(),closed).to_matrix())'''
new='''                        grasp_rotation=right_open_local[n].to_quaternion().slerp(right_closed_local[n].to_quaternion(),closed)
                        value=mat(value.translation,value.to_quaternion().slerp(grasp_rotation,fingers_active).to_matrix())'''
assert old in source
source=source.replace(old,new)
(P/'generated_contact_v4.py').write_text(source,encoding='utf-8')
exec(compile(source,str(P/'generated_contact_v4.py'),'exec'),{'__file__':str(P/'generated_contact_v4.py')})
