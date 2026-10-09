"""Recover actual botanical root anchors, and extract the existing detailed wall socket."""
from pathlib import Path
import bpy,json,math,statistics
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Sources/StockV4'
rows=json.loads((OUT/'assets.json').read_text('utf8'));fits={}
for row in rows:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=row['fbx'])
    vs=[ob.matrix_world@v.co for ob in bpy.context.scene.objects if ob.type=='MESH' for v in ob.data.vertices]
    mn=[min(v[i] for v in vs) for i in range(3)];mx=[max(v[i] for v in vs) for i in range(3)];h=mx[2]-mn[2]
    low=[v for v in vs if v.z<=mn[2]+h*.025]
    root=[statistics.median(v.x for v in low),statistics.median(v.y for v in low),mn[2]]
    fits[row['asset']]=dict(root_blender_m=root,min_m=mn,max_m=mx,height_m=h,basal_vertices=len(low),method='median of basal 2.5 percent vertex band; preserve uniform proportions')
    print('ROOT_FIT',row['asset'].split('/')[-1],root,'size',[round(mx[i]-mn[i],3) for i in range(3)],flush=True)
(OUT/'root-fits.json').write_text(json.dumps(fits,indent=2),encoding='utf8')
bpy.ops.wm.read_factory_settings(use_empty=True)
source=ROOT.parent/'DungeonWorkshopSurface20260921/Authored/DungeonWorkshopSurfaceDetails.blend'
with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.collections=['SOURCE_UtilityDetail']
coll=dst.collections[0];bpy.context.scene.collection.children.link(coll)
socket=[]
for ob in coll.objects:
    if 'Retained service' in ob.name:continue
    print('SOCKET_SOURCE',ob.name,flush=True);socket.append(ob)
deps=bpy.context.evaluated_depsgraph_get();source_materials=json.loads((ROOT.parent/'DungeonWorkshopSurface20260921/Receipts/asset-import.json').read_text())['materials']
vertices=[];faces=[];material_paths=[];face_materials=[];uvs=[]
for ob in socket:
    ev=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps);offset=len(vertices)
    vertices.extend(list(ob.matrix_world@v.co) for v in me.vertices)
    for face in me.polygons:
        faces.append([offset+i for i in face.vertices]);name=me.materials[face.material_index].name.removeprefix('WSFinish_').split('.')[0];path=source_materials[name]
        if path not in material_paths:material_paths.append(path)
        face_materials.append(material_paths.index(path));uvs.append([list(me.uv_layers.active.data[i].uv) for i in face.loop_indices] if me.uv_layers.active else None)
(OUT/'socket-source.json').write_text(json.dumps(dict(vertices=vertices,faces=faces,face_materials=face_materials,materials=material_paths,uvs=uvs,source=str(source)),indent=1),encoding='utf8')
print('STOCK_FITTING_AUTHORED',len(fits),len(vertices),flush=True)
