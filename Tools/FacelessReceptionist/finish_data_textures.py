"""Write authored data maps without color transforms, and embed them in the source."""
import bpy,numpy as np,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V01.blend'))
for name,rough,metal,leather in [('Suit',.78,0,False),('Shirt',.84,0,False),('Shoes',.47,0,True),('Badge',.43,.75,False),('Trim',.76,0,False)]:
 size=1024;y,x=np.mgrid[0:size,0:size];rng=np.random.default_rng(607)
 height=rng.normal(0,.16,(size,size)) if leather else np.sin(x*np.pi/3)*np.sin(y*np.pi/3)*.45+np.sin((x+y)*np.pi/12)*.16
 dy,dx=np.gradient(height);n=np.stack([-dx*.18,-dy*.18,np.ones_like(height)],axis=-1);n/=np.linalg.norm(n,axis=-1)[...,None]
 orm=np.ones((size,size,3),np.float32);orm[:,:,1]=np.clip(rough+height*.025,0,1);orm[:,:,2]=metal
 for suffix,rgb in [('Normal',n*.5+.5),('ORM',orm)]:
  key='Receptionist_'+name+'_'+suffix
  im=bpy.data.images.get(key)
  if im is None:im=bpy.data.images.new(key,width=size,height=size,alpha=False)
  im.colorspace_settings.name='Non-Color'
  rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=rgb
  im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(ROOT/'Textures'/(key+'.png'));im.file_format='PNG';im.save()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V01.blend'))
receipt=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8'))
receipt['saved']=[p for p in receipt['saved'] if not ('/Textures/T_FR_Receptionist_' in p and ('_Normal.' in p or '_ORM.' in p))]
(ROOT/'ue_delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('RECEPTIONIST_LINEAR_DATA_MAPS_SAVED')
