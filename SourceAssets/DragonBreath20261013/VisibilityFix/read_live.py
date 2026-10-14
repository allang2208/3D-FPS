import json
from pathlib import Path
import unreal as u
live=[]
for c in u.ObjectIterator(u.NiagaraComponent):
    asset=c.get_asset()
    if asset and 'NS_DragonBreath' in asset.get_path_name():
        row={'path':c.get_path_name(),'active':c.is_active(),'location':str(c.get_world_location()),'visible':c.is_visible()}
        for name in ['Strength','Range','HalfAngle']+[f'Ray{i}' for i in range(9)]:
            row[name]=c.get_variable_float('User.'+name)
        for name in ['Forward','Side','Up']:row[name]=str(c.get_variable_vec3('User.'+name))
        row['Origin']=str(c.get_variable_position('User.Origin'))
        live.append(row)
p=Path('D:/FPS3D/FPSGAME/SourceAssets/DragonBreath20261013/VisibilityFix')
(p/'live-components.json').write_text(json.dumps(live,indent=2),encoding='utf-8')
print('LIVE_DRAGON_COMPONENTS',json.dumps(live))
print('CACHE_LIB',[(n,[f for f in dir(getattr(u,n)) if 'capture' in f or 'create' in f]) for n in dir(u) if 'SimCache' in n and 'Library' in n])
