"""Adapt the existing camera/lighting for the requested right-hand review."""
from pathlib import Path
P=Path(__file__).parent
source=(P.parent/'BowQuickCombatContact20260927/render_player_contact.py').read_text()
source=source.replace("[('before',P.parent/'BowQuickCombatPush20260927','generated_push_v3.py'),('after',P,'generated_contact_v4.py')]",
                      "[('after',P,'author_palm.py')]")
source=source.replace(".split('bpy.ops.wm.open_mainfile')", ".split('\\nbpy.ops.wm.open_mainfile')")
source=source.replace("data=ns['ns']['data']", "data=ns['base']['data']")
source=source.replace('(.10,.14,.32,.66)', '(.10,.14,.22,.32,.44,.66,.75)')
source=source.replace('resolution_x=960;scene.render.resolution_y=540', 'resolution_x=800;scene.render.resolution_y=450')
(P/'inspect_palm.py').write_text(source)

source=(P.parent/'BowQuickCombatContact20260927/inspect_motion.py').read_text()
source=source.replace("script=P/'generated_contact_v4.py'", "script=P/'author_palm.py'")
source=source.replace(".split('bpy.ops.wm.open_mainfile')", ".split('\\nbpy.ops.wm.open_mainfile')")
source=source.replace("data=ns['ns']['data']", "data=ns['base']['data']")
source=source.replace("np.load(P/'contact-envelope.npz')", "np.load(P.parent/'BowQuickCombatContact20260927/contact-envelope.npz')")
source=source.replace("[.08,.09,.10,.105,.11,.115,.12,.125,.13,.135,.14,.18,.22,.32,.44,.62,.63,.64,.65,.66,.68,.7]",
    "[.06,.08,.09,.10,.105,.11,.115,.12,.125,.13,.135,.14,.18,.22,.32,.44,.62,.63,.64,.65,.66,.68,.7,.75]")
source=source.replace("min(depths)", "min(depths) if depths else None")
(P/'inspect_clearance.py').write_text(source)
