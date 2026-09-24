"""Check only that the requested empty-frame repair preserves accepted frames."""
import json
from pathlib import Path
import bpy
import numpy as np

root=Path('D:/FPS3D/FPSGAME/SourceAssets/RiverSplashNatural20260924')
old=root/'CardFix/Before-EmptyFrames-20260924-100020/T_RiverSplashPacked.png'
def pixels(path):
    img=bpy.data.images.load(str(path),check_existing=False)
    img.colorspace_settings.name='Non-Color'
    data=np.empty(1024*2048*4,dtype=np.float32)
    img.pixels.foreach_get(data)
    return data.reshape((2048,1024,4))
a,b=pixels(old),pixels(root/'T_RiverSplashPacked.png')
manifest=json.loads((root/'bake-manifest.json').read_text())
valid_differences=[];blank_alpha=[];old_blank_alpha=[]
for variant in range(4):
    for frame in range(1,33):
        index=variant*32+frame-1
        x,y=index%8*128,(15-index//8)*128
        old_tile,new_tile=a[y:y+128,x:x+128],b[y:y+128,x:x+128]
        if frame in manifest['empty_frames'][str(variant)]:
            blank_alpha.append(float(new_tile[:,:,3].max()))
            old_blank_alpha.append(float(old_tile[:,:,3].max()))
        else:
            valid_differences.append(float(np.abs(new_tile-old_tile).max()))
report={'preserved_frames':len(valid_differences),'max_preserved_rgba_difference':max(valid_differences),
        'empty_frames':len(blank_alpha),'empty_alpha_max_before':max(old_blank_alpha),
        'empty_alpha_max_after':max(blank_alpha)}
(root/'CardFix/preserved-frame-comparison.json').write_text(json.dumps(report,indent=2))
print('RIVER_FRAME_COMPARISON',json.dumps(report),flush=True)
if max(valid_differences)!=0 or max(blank_alpha)!=0:raise RuntimeError('Frame preservation mismatch')
