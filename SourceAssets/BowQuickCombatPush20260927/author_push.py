"""V3: upper-riser 30 cm grip, horizontal bow, two-handed forward push."""
import bpy,math,re,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;ROOT=P.parents[1]
old=P.parent/'BowQuickCombat20260927/generated_action_v2.py'
source=old.read_text(encoding='utf-8')
header=(ROOT/'Source/FPSGAME/Weapons/Bow/BowQuickCombatMotion.h').read_text()
separation=float(re.search(r'constexpr float GripSeparationCM = ([.\d]+)f;',header)[1])

# Fit the complete hand to the upper limb's actual centreline. The bow tapers
# and curves above its wrapped grip, so translating along Z alone would miss
# the wood. Source meshes use cm and the Blender Y handedness.
with bpy.data.libraries.load(str(P.parent/'BowModular20260926/Bow_ModularParts.blend'),link=False) as (a,b):
    b.objects=['SM_Bow_BodyModular']
body=b.objects[0]
def section_center(z):
    points=[body.matrix_world@v.co for v in body.data.vertices if abs((body.matrix_world@v.co).z-z)<1.5]
    return Vector(((min(v.x for v in points)+max(v.x for v in points))*.5,
                   -(min(v.y for v in points)+max(v.y for v in points))*.5,z))
shift=section_center(.8+separation)-section_center(.8)

changes={
    'Matrix.Translation((0., .246, 10.))':
        f'Matrix.Translation(({shift.x!r}, {.246+shift.y!r}, {separation!r}))',
    '# Right palm wraps 10 cm above the left; include the live (0,32,-12) hip offset in framing.':
        '# Right palm wraps 30 cm above the left; transport the whole grasp onto the curved upper riser.',
    '10 cm above left grip; current hip offset included in camera framing':
        '30 cm above left grip; fitted to real upper-limb centreline; horizontal forward push',
    'shoulder += Vector((3., 2. if side==\'r\' else 0., 1.))*load':
        "shoulder += Vector((3., (2. if side=='r' else 0.)-20., 1.))*load",
    "pole += Vector((-1., 8. if side=='r' else -4., -5.))*load":
        "pole += Vector((-1., (8. if side=='r' else -4.)-14., -5.))*load",
}
for a,b in changes.items():
    if a not in source:raise RuntimeError('Authoring input changed: '+a)
    source=source.replace(a,b)
begin=source.index('keys = [');end=source.index('def bow_at(t):',begin)
source=source[:begin]+'''# Centre the two separated grips after the live +32 cm hip offset.
# Turn to exactly horizontal before accelerating, then preserve that plane.
keys = [
    (0., (46.,-20.,-20.), (0.,0.,-30.)),
    (G,  (48.,-44.,-9.),  (0.,0.,-42.)),
    (C,  (43.,-47.,-3.),  (0.,0.,-90.)),
    (HIT,(61.,-47.,-3.),  (0.,0.,-90.)),
    (F,  (63.,-47.,-3.),  (0.,0.,-90.)),
    (RELEASE,(47.,-42.,-8.),(0.,0.,-64.)),
    (L,  (46.,-20.,-20.), (0.,0.,-30.)),
]
'''+source[end:]
source=source.replace('angles = hand_path([(a,Vector(r)) for a,p,r in keys],t)',
'''angles = Vector(keys[-1][2])
    for (a,_,ra),(b,_,rb) in zip(keys,keys[1:]):
        if a <= t <= b:
            angles = Vector(ra).lerp(Vector(rb),smooth((t-a)/(b-a)))
            break''')
source=source.replace('# Continuous angle tracks avoid a angular-speed reset at contact.',
    '# Zero angular velocity at the ends of the turn; exact -90 degrees throughout the push.')
source=source.replace('# Torso/shoulder contribution is smaller than the bow\'s arc. The elbows\n    # trail the hands downward; each wrist shares its roll with the forearm.',
    '# Centre the shoulder girdle under the horizontal two-handed grip. Elbows\n    # follow the forward drive while the native limb lengths remain fixed.')
source=source.replace('BOW_QUICK_COMBAT_AUTHORED','BOW_HORIZONTAL_PUSH_AUTHORED')
(P/'generated_push_v3.py').write_text(source,encoding='utf-8')
(P/'grip-fit.json').write_text(json.dumps({'grip_separation_cm':separation,
    'upper_riser_centerline_delta_cm':list(shift),'horizontal_roll_degrees':-90,
    'horizontal_interval_seconds':[.22,.44],'direction':'camera +X forward'},indent=2))
exec(compile(source,str(P/'generated_push_v3.py'),'exec'),{'__file__':str(P/'generated_push_v3.py')})
