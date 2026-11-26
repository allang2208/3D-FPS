"""Create task-scoped review and backpack wrappers from standard producers."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');T=P/'Tools/ModernTacticalSet'
review=(T/'lower_pair_review.py').read_text(encoding='utf-8').replace("R=S/'CombatShirtR1'","R=S/'CombatShirtR2'")
review=review.replace("str(S/'Models/04_TacticalTrousers.blend')","str(R/'Models'/f'TS01_CombatTrousers_{rig}.blend')")
review=review.replace("bpy.data.materials.get(s))","bpy.data.materials.get({'TS01_RangerRipstop':'M_CombatRipstop','TS01_RangerNylon':'M_CombatCarrier','TS01_CharcoalStretch':'M_CombatStretch'}.get(s,s)))")
review=review.replace("[('front',(1,-5,1.5)),('back',(-1,5,1.5))]","[('back',(-1,5,1.5))]")
review=review.replace('tree.ray_cast(Vector(center+direction*30),Vector(-direction),30)','tree.ray_cast(Vector(center),Vector(direction),18)')
(T/'combat2_lower_review.py').write_text(review,encoding='utf-8')
for kind in ['capture','save']:
    # These revision writers can receive task-specific resume changes after
    # initial preparation. Their live versions are authoritative thereafter.
    if (T/f'combat2_backpack_{kind}.py').exists():continue
    source=(T/f'backpack_{kind}.py').read_text(encoding='utf-8')
    source=source.replace('ModernTacticalFitR320261114','ModernTacticalShirtR220261114')
    if kind=='capture':
        source=source.replace("'ModernTacticalEarth20261114']","'ModernTacticalEarth20261114','ModernTacticalFitR320261114']")
    (T/f'combat2_backpack_{kind}.py').write_text(source,encoding='utf-8')
print('TS01_COMBAT2_FINISH_PRODUCERS_READY')
