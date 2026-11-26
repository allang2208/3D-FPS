import bpy,json
import numpy as np
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'HairNativeCombR9'
bpy.ops.wm.read_factory_settings(use_empty=True)
report=[]
for g in json.loads((N/'RefinementR4/Inputs/native_hair.json').read_text())['groups']:
 p=N/'RefinementR4/Inputs'/g['prefix'];points=np.fromfile(str(p)+'_points.bin','<f4').reshape(-1,3);counts=np.fromfile(str(p)+'_counts.bin','<u2')
 roots=points[np.r_[0,np.cumsum(counts[:-1])]]
 hc=bpy.data.hair_curves.new(g['prefix']);hc.add_curves(counts.tolist());hc.attributes['position'].data.foreach_set('vector',points.ravel())
 r=hc.attributes.new('radius','FLOAT','POINT');radius=np.concatenate([.0032*(1-.9*np.linspace(0,1,int(c))**3) for c in counts]);r.data.foreach_set('value',radius.astype('f'))
 ob=bpy.data.objects.new(g['prefix'],hc);bpy.context.scene.collection.objects.link(ob)
 report.append({'group':g['prefix'],'bounds':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],'root_bounds':[roots.min(axis=0).tolist(),roots.max(axis=0).tolist()]})
(R/'native_geometry.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Authored/Native_Donor.blend'))
