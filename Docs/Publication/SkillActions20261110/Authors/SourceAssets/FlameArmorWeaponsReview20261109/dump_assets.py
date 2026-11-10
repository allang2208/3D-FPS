"""Read the saved active flame graphs without changing any UE asset."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API,ref
from build_fireball_assets import emitters
paths=[
 '/Game/Skills/FlameArmor20261108/SwordRestoreV11/NS_FlameArmorSword',
 '/Game/Skills/FlameArmor20261108/AllWeaponsV12/NS_FlameArmorWeapon',
 '/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103/NS_StarMarrowDenseBladeFire']
result=[]
for path in paths:
 system=u.load_asset(path);row={'asset':path,'layers':[]}
 if system is None: raise RuntimeError(path)
 for name in emitters(system):
  layer={'name':name,'inputs':[],'renderer':json.loads(API.call_method('GetRendererData',(ref(system,name,renderer=0),)).get_editor_property('property_values'))}
  for script in ['EmitterSpawnScript','EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript']:
   for module in API.call_method('GetScriptStackInputValues',(ref(system,name,script),)):
    mn=str(module.get_editor_property('module_name'))
    for item in module.get_editor_property('inputs'):
     key=str(item.get_editor_property('name'));value=str(u.RainAssetEditor.read_input(system,name,script,mn,key))
     if 'HlslExpression' in value: layer['inputs'].append(dict(script=script,module=mn,key=key,value=value))
  row['layers'].append(layer)
 result.append(row)
(OUT/'active-graphs-before.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('FLAME_GRAPHS_READ',[(r['asset'],len(r['layers'])) for r in result])
