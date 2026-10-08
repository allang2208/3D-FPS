"""Read source geometry needed for the root garment authoring pass; no rendering."""
from pathlib import Path
import bpy, json
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'TentacleDynamicsV6';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'TentacleWhipV4/BoundCongregate_TentacleV4.blend'))
rows=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    vertices=ob.data.vertices
    item={'name':ob.name,'vertices':len(vertices),'faces':len(ob.data.polygons),'materials':[m.name for m in ob.data.materials],
          'bounds':[[min(v.co[k] for v in vertices),max(v.co[k] for v in vertices)] for k in range(3)],
          'colors':[(c.name,c.domain,c.data_type) for c in ob.data.color_attributes]}
    if ob.name!='BC_Flesh':
        item['sample']=[{'p':list(v.co),'w':{ob.vertex_groups[g.group].name:round(g.weight,4) for g in v.groups if g.weight>.001}} for v in list(vertices)[::max(1,len(vertices)//8)]]
    rows.append(item)
(OUT/'source_layout.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows),flush=True)
