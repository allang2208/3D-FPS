"""Read only the source head used by Jason's native Groom binding."""
from pathlib import Path
source=Path('D:/FPS3D/FPSGAME/Tools/ModernTacticalSet/helmet_hair_capture.py').read_text(encoding='utf-8')
exec(compile(source.split("report={'completed':False")[0],__file__,'exec'))
cap=json.loads((R/'capture.json').read_text(encoding='utf-8'))
asset=cap['profiles']['Jason']['hair_styles']['curly_fade'][0]['binding']['source_skeletal_mesh']
result=geometry(u.load_asset(asset),R/'Inputs/Jason_HairSourceHead.json',True)
print('HAIR_SOURCE_HEAD_CAPTURED',result,flush=True)
