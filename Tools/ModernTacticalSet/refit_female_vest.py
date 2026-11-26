"""Replace the inherited anatomical residual field with the armor frame."""
import ast,json
from pathlib import Path
import numpy as np
from smooth_vest_frame import positions
P=Path('D:/FPS3D/FPSGAME');D=P/'SourceAssets/ModernTacticalSet20261113/Integration/Delivery'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
male=read(D/'vest_Jason_Wear.json');path=D/'vest_Kaitlin_Wear.json';female=read(path)
female['positions']=positions(male,female['bones']);female['normals']=male['normals']
source=ast.parse((P/'Tools/ModernTacticalSet/derive.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='transport_normals'],type_ignores=[]),'ts01_normals','exec'))
transport_normals(female,male['positions']);path.write_text(json.dumps(female,separators=(',',':')),encoding='utf-8')
print('TS01_FEMALE_SMOOTH_FRAME',flush=True)
