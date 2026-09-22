"""Read garment UV density and source materials for the Fabric09 authoring plan."""
import bpy,json,math
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');out=root/'Revision09';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'Authoring/WitchRebuilt_Master.blend'))
result={}
for name in ('Witch_UpperRobe','Witch_OriginalRobe_Render','WitchRebuilt_Lining'):
 obj=bpy.data.objects[name];mesh=obj.data;mesh.calc_loop_triangles();uv=mesh.uv_layers[0]
 mask=mesh.color_attributes.get('SeamRepair');groups={}
 for tri in mesh.loop_triangles:
  repaired=mask and sum(mask.data[i].color[3] for i in tri.loops)/3>.5
  group=groups.setdefault('repair' if repaired else 'original',{'world_area':0.,'uv_area':0.})
  p=[obj.matrix_world@mesh.vertices[i].co for i in tri.vertices];q=[uv.data[i].uv for i in tri.loops]
  a=(p[1]-p[0]).cross(p[2]-p[0]).length*.5;b=abs((q[1]-q[0]).cross(q[2]-q[0]))*.5
  if a>1e-12 and b>1e-14:group['world_area']+=a;group['uv_area']+=b
 for group in groups.values():
  group['uv_units_per_meter']=math.sqrt(group['uv_area']/group['world_area'])
  group['tile_repeat_4cm']=1/(group['uv_units_per_meter']*.04)
 result[name]={'groups':groups,'materials':[m.name for m in mesh.materials if m],
  'uv_layers':[v.name for v in mesh.uv_layers],
  'images':sorted(set(n.image.filepath for m in mesh.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image))}
(out/'fabric_sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
