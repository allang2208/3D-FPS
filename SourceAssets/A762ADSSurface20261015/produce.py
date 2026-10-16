"""Author a genuinely neutral data normal and the narrowly scoped repair recipe."""
import json,hashlib
from pathlib import Path
from PIL import Image
O=Path(__file__).parent; R=json.loads((O/'capture.json').read_text())
T=O/'Textures';T.mkdir(exist_ok=True)
f=T/'T_A762_FlatNormal.png'
Image.new('RGB',(16,16),(128,128,255)).save(f)
root='/Game/Weapons/A762/ADSSurface20261015'
recipe={'version':'A762-NeutralNormal-20261015','texture':{'source':str(f),'path':root+'/Textures/T_A762_FlatNormal','sha256':hashlib.sha256(f.read_bytes()).hexdigest()},'targets':[],'bindings':{}}
for path,m in R['materials'].items():
 if m.get('textures',{}).get('SurfaceNormal')!='/Engine/EngineMaterials/DefaultNormal.DefaultNormal':continue
 if not m['base'].startswith('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface'):raise RuntimeError('Unexpected material graph '+path)
 private='/Game/Weapons/A762/' in path
 dest=path.split('.')[0] if private else root+'/Materials/MI_A762_'+path.split('.')[-1].removeprefix('MI_')
 recipe['targets'].append({'source':path,'destination':dest,'clone':not private,'sha256':m['sha256'],'old_normal':m['textures']['SurfaceNormal']})
 if not private:
  for mp,mesh in R['assets'].items():
   for i,s in enumerate(mesh['slots']):
    if s['material']==path:recipe['bindings'].setdefault(mp,[]).append({'index':i,'slot':s['name'],'before':path,'after':dest})
(O/'recipe.json').write_text(json.dumps(recipe,indent=2))
print('A762_RECIPE',len(recipe['targets']),'materials;',sum(t['clone'] for t in recipe['targets']),'private copies;',len(recipe['bindings']),'mesh bindings')
