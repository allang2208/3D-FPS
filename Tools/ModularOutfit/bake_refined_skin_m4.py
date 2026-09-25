"""Use CC0 Skin Human 002 for dermal relief and colour variation on V3."""
import json,runpy
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4';ROOT=BASE/'RefinedSkinV3'
runpy.run_path(str(PROJECT/'Tools/ModularOutfit/bake_original_shape_skin.py'),init_globals={'AUTHOR_ROOT':str(ROOT),'SMOOTH_SKIN':True})
external=ROOT/'External/SkinHuman002';size=2048;tile_cm=8.
raw=np.asarray(Image.open(external/'Skin_Human_002_DISP.png').convert('L'),dtype=np.float64)/255
lo,hi=np.percentile(raw,[1,99]);field=np.clip((raw-lo)/(hi-lo),0,1)
# The public source provides the skin-line network. Very broad illumination /
# height drift is removed; the original tiny pore field supplies a second scale.
field=field-gaussian_filter(field,38,mode='wrap')
field/=max(float(np.percentile(np.abs(field),99)),.01)
height=np.clip(field,-1,1)*.0038 # 0.076 mm peak-to-peak authored dermal relief
pores=np.load(BASE/'SmoothSkinV2/SkinPores_HeightCm.npy')
pores=np.tile(pores,(4,4)).reshape(size,2,size,2).mean(axis=(1,3))
height+=pores*.60
dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*tile_cm/size)
dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*tile_cm/size)
norm=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
minimum=float(height.min());maximum=float(height.max());depth=maximum-minimum
relative=(height-minimum)/depth
rough=np.clip(.48-field*.025-pores*9,.38,.62)
packed=np.stack((norm[...,0]*.5+.5,norm[...,1]*.5+.5,relative,rough),axis=-1)
Image.fromarray(np.uint8(np.clip(packed*255+.5,0,255))).save(ROOT/'T_M4OriginalShape_SkinMicro.png')
Image.fromarray(np.uint16(np.clip(relative*65535+.5,0,65535))).save(ROOT/'SkinPores_Height16_Source.png')
np.save(ROOT/'SkinPores_HeightCm.npy',height.astype(np.float32))
rgb=np.asarray(Image.open(external/'Skin_Human_002_COLOR.png').convert('RGB'),dtype=np.float64)/255
rgb=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
mean=gaussian_filter(rgb,(52,52,0),mode='wrap')
ratio=np.clip(rgb/np.maximum(mean,.03),.65,1.35)
Image.fromarray(np.uint8(np.clip(ratio*.5*255+.5,0,255))).save(ROOT/'T_M4OriginalShape_SkinColourDetail.png')
original=json.loads((ROOT/'M4_original.json').read_text());shape=json.loads((ROOT/'M4_bare_shape.json').read_text())
uv=np.asarray(original['uv']);p=np.asarray(shape['positions']);tri=np.asarray(original['triangles']);skin=np.asarray(shape['triangle_materials'])==2
a,b,c=(p[tri[:,i]] for i in range(3));area=np.linalg.norm(np.cross(b-a,c-a),axis=1)*.5
d1=uv[:,1]-uv[:,0];d2=uv[:,2]-uv[:,0];uvarea=np.abs(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])*.5
atlas=float(np.sqrt(area[skin].sum()/uvarea[skin].sum()))
report={'source':'CC0 Katsukagi Skin Human 002 DISP and COLOR; locally authored fine pores and roughness',
 'license':'CC0','provenance':'External/SkinHuman002/provenance.json','tile_size_cm':tile_cm,'texture_size':size,
 'height_range_cm':depth,'height_zero':-minimum/depth,'tile_repeat':atlas/tile_cm,
 'normal_strength':1.20,'colour_detail_strength':.55,'height_note':'Height and normal share the same authored physical field; no WPO',
 'filtering':'gradient mip sampling; fade 24-96 texels instead of the V2 4-14 cutoff',
 'skin_profile_mfp_cm':.15,'source_SPEC_used_as_roughness':False,'runtime_tested':False}
(ROOT/'micro_surface.json').write_text(json.dumps(report,indent=2))
print('CC0_DERMAL_SKIN_AND_FINE_PORES_BAKED')
