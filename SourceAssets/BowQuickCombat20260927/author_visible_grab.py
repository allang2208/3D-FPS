"""V2: bring the right hand visibly onto the upper riser before sweeping."""
from pathlib import Path
P=Path(__file__).parent
old=P.parent/'BowQuickCombat20260926/author_action.py'
source=old.read_text(encoding='utf-8')
changes={
    '# Right palm wraps the riser just below the left, with 11 cm between grips.':
    '# Right palm wraps 10 cm above the left; include the live (0,32,-12) hip offset in framing.',
    'Matrix.Translation((0., .246, -11.))':'Matrix.Translation((0., .246, 10.))',
    '(G,  (46.,-9.,-15.),  (0.,-4.,-37.))':'(G,  (50.,-25.,-7.),  (0.,-4.,-37.))',
    '(C,  (43.,9.,-6.),    (7.,-8.,-55.))':'(C,  (48.,-14.,0.),   (7.,-8.,-48.))',
    '(HIT,(59.,-6.,-18.),  (-7.,-4.,-3.))':'(HIT,(61.,-32.,-16.), (-7.,-4.,-3.))',
    '(F,  (49.,-29.,-32.), (-12.,-12.,31.))':'(F,  (52.,-43.,-31.), (-12.,-12.,25.))',
    "(.07,target+Vector((-7.,13.,-8.)))":"(.065,target+Vector((-5.,14.,6.)))",
    "(.115,target+Vector((-1.5,3.,-1.)))":"(.11,target+Vector((0.,4.,2.)))",
    'closed = smooth((t-.072)/(G-.072))':'closed = smooth((t-.105)/(G-.105))',
    '11 cm below left grip':'10 cm above left grip; current hip offset included in camera framing',
}
for a,b in changes.items():
    if a not in source:raise RuntimeError('Authoring input changed: '+a)
    source=source.replace(a,b)
(P/'generated_action_v2.py').write_text(source,encoding='utf-8')
exec(compile(source,str(P/'generated_action_v2.py'),'exec'),{'__file__':str(P/'generated_action_v2.py')})
