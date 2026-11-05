"""Render the user-requested saved R2 action, including the moving regrip."""
from pathlib import Path
O=Path(__file__).resolve().parent
source=(O.parent/'M24QuickMeleeGrip20261104/preview.py').read_text()
source=source.replace("code=(O/'author.py').read_text().split('# Read physical assembly geometry')[0]", "code=(O/'common.py').read_text()")
source=source.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_FactoryR2_Editable.blend')
source=source.replace("for view in ('fps','arms'):draw", "for view in ('fps','arms','grip'):draw")
source=source.replace("for t in (.15,.25,.325,.46):draw", "for t in (.05,.10,.15,.25,.325,.46,.55,.65,.72):draw")
source=source.replace("'views':['fps','arms']", "'views':['fps','arms','grip']")
exec(compile(source,'saved R2 preview','exec'))
