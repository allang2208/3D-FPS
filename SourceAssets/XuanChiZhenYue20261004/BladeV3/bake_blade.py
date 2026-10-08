"""Author physical steel maps on the continuous blade's 110 x 1200 mm UV domain."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.interpolate import PchipInterpolator

P=Path(__file__).resolve().parent
finish_only='--finish-only' in sys.argv
D=P/'Textures';D.mkdir(parents=True,exist_ok=True)
profile={'z_m':[-.018,0,.18,.30,.86,1.03,1.11,1.17,1.198,1.20],
         'half_width_m':[.040,.040,.040,.0398,.037,.031,.024,.012,.00065,.00002]}
width_fn=PchipInterpolator(profile['z_m'],profile['half_width_m'])
zs=np.unique(np.r_[np.linspace(-.018,1.2,306),profile['z_m'],1.12])
tip=np.clip((zs-1.12)/.08,0,1);half=.004*(1-tip*tip*(3-2*tip))
half=np.maximum(half,.00002)
profile['stations']=[[float(z),float(width_fn(z)),float(h)] for z,h in zip(zs,half)]
if not finish_only:(P/'blade_profile.json').write_text(json.dumps(profile,indent=2))

mask=np.asarray(Image.open(P.parent/'ModelV1/Textures/Blade_Engraving_Mask.png').convert('L'),dtype=np.float32)/255
H,W=mask.shape
v,u=np.mgrid[0:H,0:W].astype(np.float32);u/=W-1;v/=H-1
z=(1-v)*1.2;x=(u-.5)*.11
width=width_fn(z).astype(np.float32)
body=np.clip((.73*width-np.abs(x))/.003,0,1)
root=np.clip((z-.125)/.035,0,1);root*=root*(3-2*root)
end=np.clip((1.195-z)/.025,0,1)
groove=gaussian_filter(mask,.85)**.90*body*root*end
rng=np.random.default_rng(1004053)
def noise(sig):
    a=gaussian_filter(rng.normal(size=(H,W)).astype(np.float32),sig,mode='reflect')
    return np.clip(a/max(float(a.std()),1e-6),-2.5,2.5)
brush=noise((18,.65));forged=noise((70,13));fine=noise((.65,.50))
lip=np.clip(gaussian_filter(groove,2.0)-groove,0,1)
height=-.00014*groove+.000006*lip+.00000040*brush+.00000015*fine
dy,dx=np.gradient(height,1.20/(H-1),.11/(W-1))
normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
edge=np.clip((np.abs(x)/np.maximum(width,1e-7)-.73)/.10,0,1)
tone=1+.035*brush+.027*forged+.006*fine-.18*groove+.035*edge
color=np.array([208,216,224],dtype=np.float32)[None,None,:]/255*tone[...,None]
rough=np.clip(.32+.026*brush+.034*forged+.008*fine+.060*groove-.09*edge,.22,.48)
ao=np.clip(1-.21*groove,0,1)
orm=np.stack([ao,rough,np.full_like(ao,.97)],axis=-1)
relief=np.stack([np.clip(1+height/.00016,0,1),np.zeros_like(ao),body*root*end],axis=-1)
for name,arr in [('BaseColor',color),('Normal',normal*.5+.5),('ORM',orm),('Relief',relief)]:
    if finish_only and name not in ('BaseColor','ORM'):continue
    Image.fromarray(np.uint8(np.clip(arr,0,1)*255+.5)).save(D/('Blade_'+name+'.png'))
(P/'surface_recipe.json').write_text(json.dumps({'revision':'BladeV3','body_thickness_mm':8,
    'finish':'bright silver blade; bright copper hilt metal via original atlas mask',
    'blade_srgb_palette_255':[208,216,224],'roughness_base':.32,'metallic':.97,
    'constant_thickness_through_z_cm':112,'tip_z_cm':120,'engraving_depth_mm':.14,
    'pom_max_depth_cm':.016,'texture_size':[W,H],'normal_encoding':'OpenGL; flip green on UE import',
    'texture_residency':{'never_stream':True,'lod_bias':0,'color_group':'Weapon','normal_group':'WeaponNormalMap','scope':'Four blade maps only'},
    'ornaments':'V1 original geometry and UV; V2 existing hilt material',
    'blade':'single continuous mesh, buried root to tip; no inherited blade collar',
    'testing':'not run; user controlled'},indent=2))
print('XUANCHI_BLADE_V3_TEXTURES_AUTHORED',flush=True)
