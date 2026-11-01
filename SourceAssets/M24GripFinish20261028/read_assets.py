import json, unreal as u
from pathlib import Path
O=Path(__file__).resolve().parent
old=O.parent/'M24ArmRebuild20261027'
code=(old/'read_assets.py').read_text()
code=code.replace("O/'source_before.json'", "O.parent/'M24ArmRebuild20261027/source_after.json'")
code=code.replace(" if role.endswith('_mag10'):continue", " base_role=role.removesuffix('_mag10')")
code=code.replace("role in ('idle','aim')", "base_role in ('idle','aim')")
code=code.replace("+'/Animations/A_M24_'+role", "+'/Animations/A_M24_'+base_role")
code=code.replace("frames=sorted(set([0, min(count-1,round(count*.3)),min(count-1,round(count*.5)),count-1]))", "frames=list(range(count))")
exec(compile(code,str(old/'read_assets.py'),'exec'))
