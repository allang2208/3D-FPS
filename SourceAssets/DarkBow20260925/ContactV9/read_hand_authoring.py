"""Prepare local hand skinning and contact frames for the Bow-only repair."""
from pathlib import Path
import bpy,json
P=Path(__file__).parent
scope={'__file__':str(P/'reference_hand_frame.py')}
source=(P/'reference_hand_frame.py').read_text()
exec(compile(source.split('bpy.ops.wm.read_factory_settings')[0],scope['__file__'],'exec'),scope)
R=scope['R'];rest=scope['rest'];mat=scope['mat'];Vector=scope['Vector']
delta=scope['hand_basis']('r',(1,0,0),(0,1,0))
hand=mat((0,0,0),delta@rest['hand_r'].to_3x3())
world=scope['pose']('Hold',0)
to_hand=hand@world['hand_r'].inverted()
report={'rest':{n:[list(v) for v in m] for n,m in rest.items()},
    'parent':scope['parent'],'order':scope['order'],'hand':[list(v) for v in hand],
    'v8_pose':{n:[list(v) for v in to_hand@m] for n,m in world.items()},
    'anatomy':scope['anatomy']['r']}
report['string_rays']={key:list((to_hand@(world['bow_grip']@Vector(point)))-(to_hand@(world['bow_grip']@Vector((-50.,-.935,1.5)))))
    for key,point in [('upper',(-21.46,-.935,64.11)),('lower',(-21.46,-.935,-64.04))]}
import math
from mathutils import Matrix
report['string_rays_by_q']={}
for q in (0.,.5,1.):
    bow_r=Matrix.Rotation(math.radians(-28*q),3,'Z')@Matrix.Rotation(math.radians(-12+7*q),3,'X')
    hand_r=Matrix.Rotation(math.radians(-20*q),3,'Z')
    hand_delta=scope['hand_basis']('r',hand_r@Vector((1,0,.06)),hand_r@Vector((0,1,0)))
    mapping=delta@hand_delta.transposed()@bow_r
    anchor=Vector((-21.46,-.935,1.5)).lerp(Vector((-50.,-.935,1.5)),q)
    report['string_rays_by_q'][str(q)]={key:list(mapping@(Vector(point)-anchor))
        for key,point in [('upper',(-21.46,-.935,64.11)),('lower',(-21.46,-.935,-64.04))]}
(P/'hand_authoring_input.json').write_text(json.dumps(report),encoding='utf-8')
for d in ('thumb','index','middle','ring','pinky'):
    print(d,[(i,tuple(round(x,2) for x in (to_hand@world[f'{d}_{i:02}_r']).translation)) for i in (1,2,3)])
print('V8_NOCK_IN_HAND',tuple(round(x,3) for x in (to_hand@world['bow_nock']).translation))
