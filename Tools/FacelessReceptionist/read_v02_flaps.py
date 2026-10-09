import bpy,json
from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007\V02')
bpy.ops.wm.open_mainfile(filepath=str(p/'Authoring/FacelessReceptionist_V02.blend'))
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 bad=[v for v in o.data.vertices if .25<abs(v.co.x)<.5 and .98<v.co.z<1.16]
 if bad:
  print('FLAP',o.name,len(bad))
  for v in bad[::max(1,len(bad)//3)]:
   print('V',list(v.co),[(o.vertex_groups[g.group].name,round(g.weight,3)) for g in v.groups])
 print('PART',o.name,len(o.data.vertices),sum(len(f.vertices)-2 for f in o.data.polygons))
