"""Correct pale native strokes and the inscriptions above the guard crest."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
P=Path(__file__).resolve().parent
N=P.parent/'NativeRuneGold20260922'
src=P.parent/'RuneSword20260913/Original/Meshy_AI_Azure_Starblade_0913123202_texture_fbx/Meshy_AI_Azure_Starblade_0913123202_texture.png'
rgb=np.asarray(Image.open(src).convert('RGB'),np.float32)/255
r,g,b=np.moveaxis(rgb,-1,0);chroma=np.minimum(g-r,b-r)
d=np.load(P/'surface_mapping.npz');receipt=[]
for part,name in [('blade','T_RuneSword_NativeMask'),('guard','T_RuneSword_GuardNativeMask')]:
    cover=d[part+'_coverage'];xyz=d[part+'_xyz']
    # Only the original engraved strips above the crest belong to blade runes.
    # The guard emblem, leather, wings and crystals retain their own appearance.
    region=cover if part=='blade' else cover&(xyz[:,:,2]>.06)&(np.abs(xyz[:,:,0])<.052)
    root=xyz[:,:,2]<.24
    weak=region&(chroma>np.where(root,.018,.028))&(b>g*.88)
    strong=region&(chroma>np.where(root,.055,.10))&(b>g*.92)
    ink=ndi.binary_propagation(strong,mask=weak)
    strength=np.clip((chroma-np.where(root,.012,.025))/np.where(root,.045,.07),0,1)
    core=(strength*ink).astype(np.float32)
    core=np.maximum(core,ndi.gaussian_filter(core,.4)*.75)*region
    halo=np.clip(ndi.gaussian_filter(core,.85)-core*.6,0,1)*region
    # Both modules share one physical root-to-tip phase; no reset at the cut.
    phase=np.clip((xyz[:,:,2]-.06)/(.811727-.06),0,1)
    packed=np.stack((core,halo,phase),axis=2)
    distance,near=ndi.distance_transform_edt(~cover,return_indices=True)
    pad=(~cover)&(distance<=3)
    packed[pad]=packed[near[0][pad],near[1][pad]]
    file=P/(name+'.png')
    Image.fromarray(np.uint8(np.round(np.clip(packed,0,1)*255))).save(file)
    Image.fromarray(np.uint8(np.round(core*255))).save(P/(part+'_native_ink.png'))
    receipt.append(dict(part=part,mask=str(file),ink_pixels=int((core>.5).sum()),scope='UV0 actual module; root z > 0.06m, abs(x) < 0.052m' if part=='guard' else 'UV0 actual blade'))
# Keep the established source path reproducible and update its bake entry point.
import shutil
shutil.copy2(P/'T_RuneSword_NativeMask.png',N/'T_RuneSword_NativeMask.png')
shutil.copy2(P/'blade_native_ink.png',N/'native_ink_mask.png')
(P/'mask_receipt.json').write_text(json.dumps({'source_color':str(src),'channels':{'R':'native ink','G':'narrow halo','B':'shared physical height .06 to .811727 m'},'masks':receipt,'reason':'blade/guard split at 0.125m; pale atlas strokes below old strong threshold'},indent=2),encoding='utf-8')
print('NATIVE_ROOT_MASKS_BAKED',[(x['part'],x['ink_pixels']) for x in receipt])
