import bpy,numpy as np
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/ExtMagContinuity20260919/M4_ExtMag_Continuous_Editable.blend')
o=next(x for x in bpy.context.scene.objects if x.type=='MESH');m=o.data
im=next(n.image for n in m.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and 'BaseColor' in n.image.name);pixels=np.array(im.pixels[:]).reshape(im.size[1],im.size[0],4)
for upper in [True,False]:
 ps=[p for p in m.polygons if (p.center.z>-.20)==upper and p.center.x<.061]
 uv=np.array([m.uv_layers[0].data[i].uv[:] for p in ps for i in p.loop_indices]);color=pixels[(uv[:,1]*im.size[1]).astype(int)%im.size[1],(uv[:,0]*im.size[0]).astype(int)%im.size[0],:3]
 print('REGION',upper,'uv',uv.min(0),uv.max(0),'COLOR',np.quantile(color,[0,.5,1],axis=0),'face normalX',np.quantile([p.normal.x for p in ps],[0,.5,1]))
