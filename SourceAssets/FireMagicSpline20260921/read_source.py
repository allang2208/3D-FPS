import sys,json
from pathlib import Path
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,LIB,ref,emitters
root=Path(u.Paths.project_dir()).resolve()/'SourceAssets/FireMagicSpline20260921';root.mkdir(parents=True,exist_ok=True)
system=u.load_asset('/Game/_SplineVFX/NS/NS_Spline_Fire')
data=[]
for name in emitters(system):
    row={'emitter':name,'renderers':[]}
    top=API.call_method('GetEmitterTopology',(ref(system,name),))
    row['topology']=str(top)
    for i in range(3):
        try:
            renderer=json.loads(API.call_method('GetRendererData',(ref(system,name,renderer=i),)).get_editor_property('property_values'))
            row['renderers'].append(renderer)
        except Exception:break
    if name.startswith('Fire'):
        row['inputs']={}
        for stage in ['EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript']:
            row['inputs'][stage]=str(API.call_method('GetScriptStackInputValues',(ref(system,name,stage),)))
    data.append(row)
(root/'spline-fire-source.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps([{'emitter':r['emitter'],'renderers':r['renderers']} for r in data],indent=2))
