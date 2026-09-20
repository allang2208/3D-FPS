"""Extract an unlettered receiver-metal patch, not the weapon atlas, for UV3."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;S=O.parent;(O/'Textures').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'))
maps={}
for k in ('BaseColor','Metallic','Roughness','Normal'):
 im=bpy.data.images.load(str(S/'M16A2Migration20260919/Textures'/('m16a2_'+k+'.png')),check_existing=False)
 if k!='BaseColor':im.colorspace_settings.name='Non-Color'
 a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);maps[k]=a.reshape(im.size[1],im.size[0],4)
o=bpy.data.objects['M16A2_Receiver'];uv=o.data.uv_layers.active.data;h,w=maps['Metallic'].shape[:2];candidates=[];radius=24
for f in o.data.polygons:
 if f.area<.00001:continue
 p=np.mean([tuple(uv[i].uv) for i in f.loop_indices],axis=0);x=int(p[0]*w);y=int(p[1]*h)
 if min(x,y)<radius or x>=w-radius or y>=h-radius:continue
 region=np.s_[y-radius:y+radius,x-radius:x+radius]
 m=maps['Metallic'][region][:,:,0];c=maps['BaseColor'][region][:,:,:3];n=maps['Normal'][region][:,:,:2]
 if m.min()<.65 or c.max()>.45:continue
 score=float(c.var()+n.var()*.08+maps['Roughness'][region][:,:,0].var()*.1)
 candidates.append((score,x,y))
if not candidates:raise RuntimeError('No clean receiver coating patch found')
score,x,y=min(candidates);receipt={'reference':'M_M16A2_PBR direct texture connections','receiver_uv_center':[x/w,y/h],'source_patch_pixels':[x-radius,y-radius,48,48],'coating_uv_channel':3,'tile_metres':.04,'textures':{}}
for k,a in maps.items():
 crop=a[y-radius:y+radius,x-radius:x+radius].copy()
 # Mirroring closes all tile edges. Normal X/Y reverse on mirrored halves.
 mirrorx=crop[:,::-1].copy()
 if k=='Normal':mirrorx[:,:,0]=1-mirrorx[:,:,0]
 top=np.concatenate((crop,mirrorx),axis=1);bottom=top[::-1].copy()
 if k=='Normal':bottom[:,:,1]=1-bottom[:,:,1]
 tile=np.concatenate((top,bottom),axis=0);n=tile.shape[0]
 im=bpy.data.images.new('M16_Coat_'+k,width=n,height=n,alpha=True)
 im.colorspace_settings.name='sRGB' if k=='BaseColor' else 'Non-Color';im.pixels.foreach_set(tile.reshape(-1));im.filepath_raw=str(O/'Textures'/('T_M16_Coat_'+k+'.png'));im.file_format='PNG';im.save()
 receipt['textures'][k]={'file':im.filepath_raw,'mean':crop.mean(axis=(0,1)).tolist()}
(O/'coating.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('M16_RECEIVER_COATING_AUTHORED',x,y,flush=True)
