"""Extract a coverage channel before UE builds mips; preserve the source artwork."""
import bpy,numpy as np,json
from pathlib import Path
P=Path(__file__).parent;P.joinpath('RuneMasks').mkdir(exist_ok=True)
report={}
for key in ['resonance_rune','erosion_rune','conduction_rune']:
    src=bpy.data.images.load(str(P.parent/'MeleeRuneMods20260915/Generated'/(key+'.png')))
    src.colorspace_settings.name='Non-Color'
    w,h=src.size;pixels=np.empty(w*h*4,np.float32);src.pixels.foreach_get(pixels);pixels=pixels.reshape(h,w,4)
    luma=pixels[:,:,:3]@np.array([.2126,.7152,.0722],np.float32)
    v=np.clip((luma-.62)/(.94-.62),0,1);mask=v*v*(3-2*v)*pixels[:,:,3]
    image=bpy.data.images.new('Mask_'+key,width=w,height=h,alpha=False);image.colorspace_settings.name='Non-Color'
    out=np.ones((h,w,4),np.float32);out[:,:,:3]=mask[:,:,None];image.pixels.foreach_set(out.ravel())
    image.filepath_raw=str(P/'RuneMasks'/(key+'.png'));image.file_format='PNG';image.save()
    # Record the actual loss caused by threshold-after-minification versus
    # filtering the already-extracted coverage, using the same source image.
    rows=[]
    for scale in [4,8,16,32]:
        hh=h//scale;ww=w//scale
        lm=luma[:hh*scale,:ww*scale].reshape(hh,scale,ww,scale).mean(axis=(1,3))
        am=pixels[:hh*scale,:ww*scale,3].reshape(hh,scale,ww,scale).mean(axis=(1,3))
        v=np.clip((lm-.62)/.32,0,1);old=v*v*(3-2*v)*am
        new=mask[:hh*scale,:ww*scale].reshape(hh,scale,ww,scale).mean(axis=(1,3))
        rows.append({'mip_scale':scale,'old_mean_coverage':float(old.mean()),'new_mean_coverage':float(new.mean())})
    report[key]=rows
(P/'rune_mip_diagnosis.json').write_text(json.dumps(report,indent=2));print('RUNE_MASKS_READY',json.dumps(report),flush=True)
