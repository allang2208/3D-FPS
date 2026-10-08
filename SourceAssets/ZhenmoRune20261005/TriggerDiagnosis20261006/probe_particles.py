import builtins,sys,json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(u.Paths.project_dir())/'Tools/Skills'))
from build_fireball_assets import API,ref
s=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold')
r={}
for en,module,stage in [('BaguaRisingGold','EmitterState','EmitterUpdateScript'),('','SystemState','SystemUpdateScript')]:
    for name in ['Scalability Mode','Enable Visibility Culling','Cull By Global Budget','Max Time Without Render','Max Time Without Render Response','Enable Distance Culling','MinDistance','MaxDistance','Inactive Response','Loop Behavior']:
        try:r[en+'/'+name]=u.RainAssetEditor.read_input(s,en,stage,module,name)
        except Exception as ex:r[en+'/'+name]=str(ex)
(OUT/'particle_state_inputs.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('PARTICLE_STATE '+json.dumps(r))
