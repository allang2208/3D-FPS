"""Read only the four new packages before background authoring alongside PIE."""
import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/ApartmentFastRest20261024R2')
rows=[]
for base,prefix in [('/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/','A_'),('/Game/Characters/KaitlinPlayer20261023/','K_A_')]:
    for phase in ('Enter','Exit'):
        name=prefix+'Rest_ApartmentBed_'+phase;path=base+OUT.name+'/'+name
        rows.append({'path':path,'loaded':u.find_object(None,path+'.'+name) is not None})
if any(r['loaded'] for r in rows):raise RuntimeError('A destination package is already loaded; preserve the editor copy.')
(OUT/'background_target_ownership.json').write_text(json.dumps(rows,indent=2))
print('FAST_REST_NEW_DESTINATIONS_UNLOADED',len(rows))
