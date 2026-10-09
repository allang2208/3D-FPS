"""Remove the two identified loose islands from the actual trousers mesh."""
import bpy,json
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');ROOT=BASE/'V07'
for folder in ['Authoring','Delivery','Logs']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
evidence=json.loads((ROOT/'fragment_source.json').read_text(encoding='utf-8'))
parts=evidence['mesh_components']['Security_Trousers_Continuous']
targets=[p for p in parts if p['id'] in [1,2]]
if [p['vertices'] for p in targets]!=[96,86]:raise RuntimeError('The identified V06 trouser islands are not available')
remove={i for part in targets for i in part['vertex_indices']}
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V06/Authoring/FacelessSecurity_V06.blend'))
pants=bpy.data.objects['Security_Trousers_Continuous'];old=pants.data
if len(old.vertices)!=28544:raise RuntimeError('Unexpected source trousers; preserve this version for investigation')

# Rebuild only this mesh's index buffers, retaining the exact coordinates,
# UVs, normals, material indices and weights of every surviving corner.
keep=[v.index for v in old.vertices if v.index not in remove]
remap={old_index:new_index for new_index,old_index in enumerate(keep)}
faces=[f for f in old.polygons if not any(i in remove for i in f.vertices)]
coordinates=[old.vertices[i].co.copy() for i in keep]
weights=[[(g.group,g.weight) for g in old.vertices[i].groups] for i in keep]
group_names=[g.name for g in pants.vertex_groups]
loop_ids=[i for f in faces for i in f.loop_indices]
normals=[old.corner_normals[i].vector.copy() for i in loop_ids]
uvs={layer.name:[layer.data[i].uv.copy() for i in loop_ids] for layer in old.uv_layers}
materials=list(old.materials);surface_flags=[(f.material_index,f.use_smooth) for f in faces]
new=bpy.data.meshes.new('Security_Trousers_Continuous_V07')
new.from_pydata(coordinates,[],[tuple(remap[i] for i in f.vertices) for f in faces]);new.update()
for material in materials:new.materials.append(material)
for face,(material_index,smooth) in zip(new.polygons,surface_flags):face.material_index=material_index;face.use_smooth=smooth
for name,values in uvs.items():
    layer=new.uv_layers.new(name=name)
    for item,value in zip(layer.data,values):item.uv=value
new.normals_split_custom_set(normals)
pants.data=new;pants.vertex_groups.clear()
for name in group_names:pants.vertex_groups.new(name=name)
for i,row in enumerate(weights):
    for group,weight in row:pants.vertex_groups[group].add([i],weight,'REPLACE')
report={'source':'V06','object':pants.name,'removed_components':[{'id':p['id'],'vertices':p['vertices'],'triangles':p['triangles'],'weights':p['weights']} for p in targets],
    'removed_vertices':len(remove),'removed_triangles':sum(p['triangles'] for p in targets),
    'retained_vertices':len(new.vertices),'retained_triangles':sum(len(f.vertices)-2 for f in new.polygons),
    'preserved':'All other objects, surviving trouser coordinates/UVs/normals/weights, skeleton, materials and V06 motions',
    'game_tested':False,'rendered':False}
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V07.blend'))
(ROOT/'fragment_removal.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SECURITY_WAIST_FRAGMENT_REMOVED '+json.dumps(report),flush=True)
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V07')
exec(compile(export,'export_security_v07','exec'))
