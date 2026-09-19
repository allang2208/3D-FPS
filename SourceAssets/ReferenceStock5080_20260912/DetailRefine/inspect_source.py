import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ReferenceStock5080_Game_Editable.blend'))
o=bpy.data.objects['Generated_Textured_Master'];points=np.array([v.co[:] for v in o.data.vertices]);r={'bounds':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],'sections':{}}
for x in [0,.5,1,2,5,7,10,12,13,14,15,16,17,18,19,20,21,22,22.5,23]:
 p=points[abs(points[:,0]-x)<.06]
 r['sections'][x]={'count':len(p),'min':p.min(axis=0).tolist() if len(p) else None,'max':p.max(axis=0).tolist() if len(p) else None}
(P/'source_sections.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
bpy.ops.wm.open_mainfile(filepath=str(P.parent.parent/'SkeletonStock20260912/m4_fit_reference.blend'))
rows=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not ('Receiver' in o.name or 'Body' in o.name):continue
 for m in o.data.materials:
  rows.append({'object':o.name,'material':m.name,'images':[{'name':n.image.name,'path':bpy.path.abspath(n.image.filepath)} for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]})
(P/'m4_source_materials.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
