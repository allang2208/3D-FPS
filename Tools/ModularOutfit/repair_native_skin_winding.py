"""Migrate existing v1 surfaces to the corrected UE winding, without changing anatomy."""
import json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/NativeSkin')
count=0
for key in json.loads((root.parent/'inputs.json').read_text()):
    path=root/(key+'_skin.json')
    data=json.loads(path.read_text())
    if data.get('surface_export_version',1)>=2:continue
    data['triangles']=[t[::-1] for t in data['triangles']]
    data['surface_export_version']=2
    path.write_text(json.dumps(data,separators=(',',':')))
    count+=1
print('NATIVE_SKIN_WINDING_MIGRATED',count)
