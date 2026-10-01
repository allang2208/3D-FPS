import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent;H=S/'HK416Reworked20260930'
I=json.loads((H/'authoring.json').read_text());R=Matrix(I['root_matrix']);sources=json.loads((S/'M16UniversalAttachments20260920/sources.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
result={'native':{},'stocks':{}}
def describe(ob,axis):
 points=[v.co for v in ob.data.vertices];areas={}
 for f in ob.data.polygons:
  if abs(f.normal[axis])<.9:continue
  p=round(f.center[axis],5);areas[p]=areas.get(p,0)+f.area
 return {'bounds':[[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)],'end_planes':sorted(areas.items(),key=lambda a:-a[1])[:16],'materials':[m.name for m in ob.data.materials]}
names=['Stock_ring_low','Stock_Stick_low','Stock_body_low','Shock_Res_low','Lower_body_low','Hand_grip_low']
with bpy.data.libraries.load(str(H/'HK416_Gameplay_Editable.blend'),link=False) as (a,b):b.objects=names
for ob in b.objects:
 bpy.context.collection.objects.link(ob);ob.data.transform(R.inverted()@ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.update();result['native'][ob.name]=describe(ob,1)
for key in ('skeleton','qr_performance','core_stock','tactical_telescopic'):
 before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=sources[key]['fbx'],use_custom_normals=True)
 meshes=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH' and not o.name.startswith(('UCX_','UBX_'))]
 rows=[]
 for ob in meshes:ob.data.transform(ob.matrix_world);ob.data.update();rows.append(describe(ob,0))
 result['stocks'][key]=rows
(O/'geometry_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('HK416_REPAIR_GEOMETRY_INPUTS_READ')
