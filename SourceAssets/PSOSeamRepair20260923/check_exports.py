"""User-requested focused check: exported opaque seams and real lens partition."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;data=json.loads((O/'authoring.json').read_text());result=[]
for row in data['meshes']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=row['fbx'],use_anim=False)
 materials={};collars=[];glass=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  for p in ob.data.polygons:
   name=ob.data.materials[p.material_index].name
   materials[name]=materials.get(name,0)+len(p.vertices)-2
   if 'ScopeLens' in ob.name:
    (glass if 'Lens' in name or 'OpticalGlass' in name else collars).append(p.index)
 if len(collars)!=340 or len(glass)!=15:raise RuntimeError('Export lost PSO partition '+row['host']+' '+str((len(collars),len(glass))))
 result.append({'host':row['host'],'opaque_collar_triangles':len(collars),'glass_triangles':len(glass),'material_triangle_counts':materials,'passed':True})
(O/'export_checks.json').write_text(json.dumps(result,indent=2))
print('PSO_EXPORT_PARTITION_CHECKED',len(result),flush=True)
