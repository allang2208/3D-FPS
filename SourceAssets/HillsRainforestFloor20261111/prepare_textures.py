"""Pack the downloaded Quixel scan for runtime use; originals remain unchanged."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

BATCH=Path(__file__).resolve().parent
OUT=BATCH/'Textures'
OUT.mkdir(exist_ok=True)
scans=[
    ('Source','Mossy_Forest_Floor_vfylbge_2K_','T_RainforestMoss_','vfylbge',100),
    ('JungleSource','Jungle_Ground_tjckaf3g_2K_','T_JungleGround_','tjckaf3g',200)]
report=[]
for directory,prefix,dest,scan_id,scale in scans:
    def read(kind):
        return Image.open(BATCH/directory/(prefix+kind+'.jpg'))
    for kind in ('BaseColor','Normal'):
        read(kind).convert('RGB').save(OUT/(dest+kind+'.png'))
    ao=read('AO').convert('L')
    rough=read('Roughness').convert('L')
    raw=np.asarray(read('Displacement').convert('L'),dtype=np.float32)
    lo,hi=np.percentile(raw,[1,99])
    height=Image.fromarray((np.clip((raw-lo)/max(hi-lo,1),0,1)*255).astype(np.uint8))
    Image.merge('RGB',(ao,rough,height)).save(OUT/(dest+'ARH.png'))
    report.append({'scan_id':scan_id,'scan_size_cm':scale,'height_source_range':[float(lo),float(hi)]})
(BATCH/'Receipts/texture-packing.json').write_text(json.dumps({
    'scans':report,'channels':{'R':'AO','G':'Roughness','B':'Height, normalized 1-99 percentile'},
    'base_color_modified':False,'source_files_modified':False},indent=2),encoding='utf-8')
print('Prepared six rainforest surface textures.')
