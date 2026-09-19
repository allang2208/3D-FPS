import bpy, json, numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
paths={
 'tactical':P/'TacticalTelescopic/Imported_Source.blend',
 'skeleton':Path('D:/FPS3D/FPSGAME/SourceAssets/ReferenceStock5080_20260912/DetailRefine/m4/Stock_Refined_Editable.blend'),
 'performance':Path('D:/FPS3D/FPSGAME/SourceAssets/MeshyPerformanceStock20260913/M4/PerformanceStock_Editable.blend'),
 'core':Path('D:/FPS3D/FPSGAME/SourceAssets/CoreStock20260914/Meshy0914005605/M4/CoreStock_Game_Editable.blend'),
 'factory':Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend')}
report={}
for key,path in paths.items():
 bpy.ops.wm.open_mainfile(filepath=str(path)); entries=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or (key=='factory' and 'Stock' not in o.name):continue
  verts=np.array([tuple(o.matrix_world@v.co) for v in o.data.vertices]);entry={'name':o.name,'hidden':o.hide_render,'min':verts.min(axis=0).tolist(),'max':verts.max(axis=0).tolist(),'materials':[m.name for m in o.data.materials if m]}
  if key=='tactical':
   entry['front_slices']=[]
   for width in [.01,.03,.06,.12]:
    q=verts[verts[:,0]<verts[:,0].min()+width];entry['front_slices'].append({'width':width,'min':q.min(axis=0).tolist(),'max':q.max(axis=0).tolist()})
  entries.append(entry)
 report[key]={'path':str(path),'objects':entries,'images':[{'name':im.name,'path':im.filepath,'packed':bool(im.packed_file)} for im in bpy.data.images]}
(P/'stock_source_inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
