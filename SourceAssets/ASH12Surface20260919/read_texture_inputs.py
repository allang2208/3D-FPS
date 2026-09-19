"""Read source encoding to choose the authoring decode, no asset changes."""
import bpy, numpy as np
for p in ['D:/FPS3D/资产/oden先辈/natga/upper_n.tga','D:/FPS3D/FPSGAME/SourceAssets/ASH1220260917/Textures/T_ASH12_Upper_Normal.png']:
    im=bpy.data.images.load(p); im.colorspace_settings.name='Non-Color'
    a=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(a)
    a=a.reshape(im.size[1],im.size[0],4)
    print(p, im.size[:], 'center',a[1000,1000,:], 'median',np.median(a.reshape(-1,4),axis=0),'range',a.min((0,1)),a.max((0,1)))
