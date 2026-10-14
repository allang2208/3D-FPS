"""Read the imported Fab flame system for Dragon Breath authoring; no gameplay."""
import json
import sys
from pathlib import Path
import unreal as u
root=Path(u.Paths.project_dir())
sys.path.insert(0,str(root/'Tools/Skills'))
from build_fireball_assets import API,ref,emitters
asset=u.load_asset('/Game/RPG-FlameAttackVFX/VFX/Niagara/N_FlameAttack')
if not asset: raise RuntimeError('Imported Fab flame system is missing')
out={'asset':asset.get_path_name(),'summary':API.call_method('GetSystemSummary',(asset,)).export_text(),'emitters':{}}
out['values']={}
for name in emitters(asset):
    out['emitters'][name]=API.call_method('GetEmitterTopology',(ref(asset,name),)).export_text()
    out['values'][name]={'settings':API.call_method('GetEmitterData',(ref(asset,name),)).export_text(),
        'renderer':API.call_method('GetRendererData',(ref(asset,name,renderer=0),)).export_text()}
    for stage in ['EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript']:
        out['values'][name][stage]=[v.export_text() for v in API.call_method('GetScriptStackInputValues',(ref(asset,name,stage),))]
dest=root/'SourceAssets/DragonBreath20261013';dest.mkdir(parents=True,exist_ok=True)
(dest/'source-topology.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('DRAGON_BREATH_SOURCE_READ '+str(dest/'source-topology.json'))
