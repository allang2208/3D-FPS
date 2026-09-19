"""Read the front cross section to choose the actual tube center for authoring."""
import bpy,numpy as np,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Imported_Source.blend'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
p=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices]);res=[]
for a,b in [(-.952,-.949),(-.950,-.94),(-.94,-.92),(-.92,-.90),(-.90,-.86)]:
    s=p[(p[:,0]>=a)&(p[:,0]<b)];rows=[]
    for z in np.arange(.10,.70,.025):
        t=s[(s[:,2]>=z)&(s[:,2]<z+.025)]
        if len(t):rows.append([round(z,3),len(t),round(float(t[:,1].min()),5),round(float(t[:,1].max()),5)])
    res.append({'x':[a,b],'z_bins_count_ymin_ymax':rows})
(P/'mount_coordinates.json').write_text(json.dumps(res,indent=2))
