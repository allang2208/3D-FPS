"""Freeze owned modeling inputs and helper code; never runs another asset author."""
from pathlib import Path
import ast,json,shutil,hashlib
P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/ArcaneConduitBelt20261025/ModelR1'
T=Path(__file__).parent; old=P/'SourceAssets/MeleeCombatBelt20261025/ModelR1'
for name in ('Inputs','Exports','Textures','Authored','Reference','Logs'):(R/name).mkdir(parents=True,exist_ok=True)
for src in (old/'Inputs').iterdir():
    if src.is_file():shutil.copy2(src,R/'Inputs'/src.name)
inputs=json.loads((old/'inputs.json').read_text(encoding='utf-8-sig'))
for row in inputs['records']:
    row['native_reference']=str(R/'Inputs'/f"{row['body']}_NativeBody.json")
inputs['frozen_from']=str(old/'inputs.json')
(R/'inputs.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(R.parent/'ConceptR1/design-sheet.png',R/'Reference/approved-design.png')
shutil.copy2(R.parent/'ConceptR1/wearing-reference.png',R/'Reference/wearing-concept.png')
source=P/'Tools/MeleeCombatBelt'
native=(source/'native_geometry.py').read_text(encoding='utf-8-sig')
native=native.replace('SourceAssets/MeleeCombatBelt20261025/ModelR1','SourceAssets/ArcaneConduitBelt20261025/ModelR1')
native=native.replace('Melee_Tonal_Stitch','Arcane_SilverGrey_Thread').replace('self.height = 9.0','self.height = 7.2')
native=native.replace('(0.07, 0.077, 0.082, 1)','(0.19, 0.20, 0.22, 1)')
(T/'native_geometry.py').write_text(native,encoding='utf-8')
shutil.copy2(source/'surface_fields.py',T/'surface_fields.py')
text=(source/'author.py').read_text(encoding='utf-8-sig'); tree=ast.parse(text)
helpers=[ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('rounded','catmull')]
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MeleeBelt')
methods=[]
for n in cls.body:
    if isinstance(n,ast.FunctionDef) and n.name in ('__init__','finish','stitch','frame','prism','ring','fastener'):
        methods.append('    '+ast.get_source_segment(text,n))
frozen='from native_geometry import *\nINDIGO,EDGE,LINING,SILVER,DARKSILVER,BRASS,THREAD,CRYSTAL,RUNE,ETCH=range(10)\nTITANIUM=SILVER;GRAPHITE=DARKSILVER\n\n'+'\n\n'.join(helpers)+'\n\nclass BeltConstruction(NativeBelt):\n'+'\n\n'.join(methods)+'\n'
frozen=frozen.replace("'破阵近战腰带'","'星律导能腰带'")
(T/'construction.py').write_text(frozen,encoding='utf-8')
sources={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'author.py',source/'native_geometry.py',source/'surface_fields.py')}
(R/'Authored/source-provenance.json').write_text(json.dumps({'frozen_helpers':sources,'inputs':str(old/'inputs.json'),'scope':'Only waist sampling, geometry primitives, native skinning and export; arcane design authored separately'},indent=2)+'\n',encoding='utf-8')
print('ARCANE_INPUTS_FROZEN',str(R),flush=True)
