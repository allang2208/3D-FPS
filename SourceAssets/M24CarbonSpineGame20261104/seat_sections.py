"""Read welded mounting and grip silhouettes from the two actual mesh exports."""
from pathlib import Path
import bpy,numpy as np
O=Path(__file__).resolve().parent
for kind in ('Native','Advanced'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(kind+'.fbx')),use_custom_normals=True)
    ob=next(o for o in bpy.data.objects if o.type=='MESH');V=np.array([ob.matrix_world@v.co for v in ob.data.vertices])
    for m in range(len(ob.data.materials)):
        faces=[p for p in ob.data.polygons if p.material_index==m];vv=V[list({i for p in faces for i in p.vertices})]
        ring=vv[np.abs(vv[:,1]+.043)<.000002];print(kind,m,'bounds',vv.min(0),vv.max(0),'end ring',len(ring),flush=True)
        if m==1:
            for y in (-.30,-.24,-.18,-.15,-.125,-.10,-.08,-.06):
                cross=[]
                for p in faces:
                    for a,b in p.edge_keys:
                        u,v=V[a],V[b]
                        if (u[1]-y)*(v[1]-y)<0:cross.append(u+(v-u)*((y-u[1])/(v[1]-u[1])))
                if cross:print('SECTION',round(y,3),np.round(np.min(cross,axis=0),4),np.round(np.max(cross,axis=0),4),flush=True)
