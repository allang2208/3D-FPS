import bpy,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_ReferenceRepair38.blend'),use_scripts=False)
rec=bpy.data.objects['Receiver'];root=bpy.data.objects['SK_M4_Infima'].data.bones['WPN_root'].matrix_local
xf=root.inverted()@rec.matrix_world;me=rec.data;me.calc_loop_triangles()
v=np.array([(xf@q.co)[:] for q in me.vertices]);f=np.array([p.vertices[:] for p in me.loop_triangles]);m=np.array([me.polygons[p.polygon_index].material_index for p in me.loop_triangles]);c=v[f].mean(1)
for name,sel in [('center', (m==1)&(c[:,0]>-.0204)&(c[:,0]<.022)&(c[:,1]>-.2149)&(c[:,1]<-.1091)),('alltop',(m==1)&(c[:,1]>-.24)&(c[:,1]<-.095)&(c[:,2]>.045))]:
 print('PROBE',name,int(sel.sum()),np.histogram(c[sel,2],bins=[.04,.048,.05,.055,.06,.064,.067,.073,.09]))
np.savez_compressed(O/'receiver_current.npz',v=v,f=f,m=m)
