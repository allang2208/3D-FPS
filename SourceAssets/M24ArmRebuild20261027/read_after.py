"""Read the saved replacement layers at source transition and contact frames."""
import json
from pathlib import Path

O = Path(__file__).resolve().parent
code = (O / 'read_assets.py').read_text()
code = code.replace('source_before.json', 'source_after.json').replace('ue_before.json', 'ue_after.json')
# Read the currently bound profile entry points after asset-only publication.
code = code.replace(" if role.endswith('_mag10'):continue", " base_role=role.removesuffix('_mag10')")
code = code.replace("role in ('idle','aim')", "base_role in ('idle','aim')")
code = code.replace("+'/Animations/A_M24_'+role", "+'/Animations/A_M24_'+base_role")
code = code.replace("frames=sorted(set([0, min(count-1,round(count*.3)),min(count-1,round(count*.5)),count-1]))",
    "frames=sorted({0,count-1,*[f for f in (3,6,8,12,16,17,20,25,30,35,40,44,48,55,60,68,69,77,87,94) if f<count]})")
exec(compile(code, str(O/'read_assets.py'), 'exec'))
