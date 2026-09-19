import bpy, numpy as np, json
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets/ReferenceSuppressor5080_20260913/seed_91353/Suppressor_5080_Candidate_Editable.blend')
bpy.ops.wm.open_mainfile(filepath=str(p))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
a=np.empty(len(o.data.vertices)*3,dtype=np.float64);o.data.vertices.foreach_get('co',a);a=a.reshape(-1,3)
lo=a.min(0);hi=a.max(0);ax=int(np.argmax(hi-lo));cross=[i for i in range(3) if i!=ax];center=(lo+hi)/2;r=np.linalg.norm(a[:,cross]-center[cross],axis=1);t=(a[:,ax]-lo[ax])/(hi[ax]-lo[ax])
print('AUTHOR_FRAME',json.dumps({'object':o.name,'matrix':[list(row) for row in o.matrix_world],'lo':lo.tolist(),'hi':hi.tolist(),'long_axis':ax,'cross_axes':cross,'custom_normals':o.data.has_custom_normals}))
for k in range(20):
 mask=(t>=k/20)&(t<(k+1)/20)
 print('OUTER_PROFILE',round(k/20,2),np.quantile(r[mask],[.4,.65,.85,.95]).tolist())
for im in bpy.data.images:
 print('SOURCE_IMAGE',im.name,list(im.size),im.colorspace_settings.name,im.packed_file.size if im.packed_file else 0)
