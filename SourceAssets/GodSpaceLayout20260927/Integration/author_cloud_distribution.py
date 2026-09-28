"""Author an 80% cloud-footprint threshold from the existing float texture.

Run with background Blender for its EXR reader and numpy. No image is generated
or edited, and this is parameter production rather than a scene coverage test.
"""
import json
from pathlib import Path
import bpy
import numpy as np
root=Path(__file__).parent/'CloudSeaSources'
image=bpy.data.images.load(str(root/'ExistingCloudPattern.exr'),check_existing=False)
pixels=np.empty(len(image.pixels),dtype=np.float32)
image.pixels.foreach_get(pixels)
width,height=image.size
rgb=pixels.reshape(height,width,4)[:,:,:3]
source=rgb@np.array([.55,.30,.15],dtype=np.float32)
# Author against the source image's periodic bilinear reconstruction. The
# editor's resident mip size can be smaller than this exported source image.
size=2048
x=(np.arange(size)+.5)*width/size-.5
y=(np.arange(size)+.5)*height/size-.5
xi=np.floor(x).astype(int);yi=np.floor(y).astype(int)
fx=(x-xi)[None,:];fy=(y-yi)[:,None]
a=source[yi[:,None]%height,xi[None,:]%width]
b=source[yi[:,None]%height,(xi[None,:]+1)%width]
c=source[(yi[:,None]+1)%height,xi[None,:]%width]
d=source[(yi[:,None]+1)%height,(xi[None,:]+1)%width]
field=(a*(1-fx)+b*fx)*(1-fy)+(c*(1-fx)+d*fx)*fy
threshold=float(np.quantile(field,.20))
feather=max(.003,min(.055,float(np.quantile(field,.29))-threshold))
settings={
    'coverage_target':.80,
    'coverage_definition':'existing weather-map footprint at its 20th percentile; not screen-space opacity',
    'threshold':threshold,'feather':feather,'texture_size':list(image.size),
    'source':'ExistingCloudPattern.exr','weights':[.55,.30,.15],
    'distribution_quantiles':{str(q):float(np.quantile(field,q)) for q in [.0,.1,.2,.5,.8,1.]},
    'cloud_layer_bottom_km':.62,'cloud_layer_height_km':.70,
    'layout_period_km':18.,'base_density_per_m':.008,
    'runtime_coverage_measured':False,
}
(root/'distribution.json').write_text(json.dumps(settings,indent=2),encoding='utf8')
print('GODSPACE_CLOUD_DISTRIBUTION_AUTHORED '+json.dumps(settings))
