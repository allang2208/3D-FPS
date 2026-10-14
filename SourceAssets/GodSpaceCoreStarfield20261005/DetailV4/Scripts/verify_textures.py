from pathlib import Path
import json,hashlib,ast
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
R=Path(__file__).resolve().parents[1];W=R.parent
O=W/'BaselineV2/Authored/Textures';N=R/'Authored/Textures'
report={'scope':'Offline source pixels and Python syntax only; not UE sampling, compilation, residency or visual acceptance','files':[],'comparisons':{}}
for f in sorted(N.glob('*.png')):
    with Image.open(f) as im:
        a=np.asarray(im);d={'name':f.name,'size':list(im.size),'mode':im.mode,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
        if f.name in ['T_CoreStarfield_BaseColor.png','T_CoreStars_Emissive.png']:
            d['seam_max_byte_delta']=int(np.max(np.abs(a[:,0].astype(int)-a[:,-1].astype(int))))
            d['north_pole_spread']=int(np.max(np.ptp(a[0].astype(int),axis=0)))
            d['south_pole_spread']=int(np.max(np.ptp(a[-1].astype(int),axis=0)))
            assert d['seam_max_byte_delta']==d['north_pole_spread']==d['south_pole_spread']==0
        report['files'].append(d)
def detail(path):
    # Same central source region; numerical descriptor, never a quality score.
    a=np.asarray(Image.open(path).convert('RGB').crop((1024,768,3072,1280)),dtype=np.float32)/255
    gray=a.mean(axis=2);base=gaussian_filter(gray,2.0);hp=gray-base
    return {'mean_gray':float(gray.mean()),'highpass_rms_over_mean':float(np.sqrt(np.mean(hp*hp))/max(gray.mean(),1e-6)),'any_channel_clipped_255_fraction':float(np.mean(a.max(axis=2)>=1.0))}
report['comparisons']['nebula_same_source_region']={'V2':detail(O/'T_CoreStarfield_BaseColor.png'),'V4':detail(N/'T_CoreStarfield_BaseColor.png')}
report['syntax_checked']=[]
for f in sorted((R/'Scripts').glob('*.py')):
    ast.parse(f.read_text(encoding='utf-8'),filename=str(f));report['syntax_checked'].append(f.name)
(R/'Receipts/source_texture_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
