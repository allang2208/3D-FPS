"""Targeted analysis requested for the invisible impact; no UE simulation."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MeteorVisibilityRepair20261114'
OUT.mkdir(parents=True,exist_ok=True)
p=ROOT/'SourceAssets/MeteorImpactReferenceV7_20261114/Blast/T_MeteorPressureFieldsV7.png'
a=np.asarray(Image.open(p),dtype=np.float32)/255
rows=[]
for i in range(64):
    frame=a[(i//8)*256:(i//8+1)*256,(i%8)*256:(i%8+1)*256]
    rows.append(dict(frame=i,max_rgb=frame[:,:,:3].max(axis=(0,1)).tolist(),
        fire_pixels_over_003=int((frame[:,:,0]>.003).sum()),
        fire_pixels_over_008=int((frame[:,:,0]>.08).sum()),
        smoke_pixels_over_003=int((frame[:,:,2]>.003).sum())))
last=max(row['frame'] for row in rows if row['fire_pixels_over_008']>0)
# Old crown drives .045 + .70 * normalized_age**.82 through all 64 tiles.
end_n=((last/63-.045)/.70)**(1/.82)
result=dict(atlas=str(p),frames=rows,last_substantial_flame_frame=last,
    old_crown_seconds_to_last_substantial_flame=.82*end_n,
    old_crown_lifetime_seconds=.82,
    conclusion='Fire and smoke require independent source frame windows.')
(OUT/'source-frame-diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf8')
manifest_path=p.parent/'atlas-manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf8'))
manifest['playback_windows']={'fire':[0,last+.65],'smoke':[0,63]}
manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='frames'},indent=2))
