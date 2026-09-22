"""Read authoring coordinates for fitting the selected sword, without rendering."""
import bpy, json
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P.parent/'Meshy/candidate01/downloads/model.glb'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
rows=[]
for obj in objects:
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
    points=[v.co for v in obj.data.vertices]
    lo=min(p.z for p in points);hi=max(p.z for p in points)
    slices=[]
    for i in range(51):
        z=lo+(hi-lo)*i/50
        section=[p for p in points if abs(p.z-z)<(hi-lo)/160]
        if section:slices.append({'z':z,'x':[min(p.x for p in section),max(p.x for p in section)],'y':[min(p.y for p in section),max(p.y for p in section)]})
    rows.append({'name':obj.name,'vertices':len(points),'triangles':len(obj.data.polygons),'bounds':[[min(p[a] for p in points),max(p[a] for p in points)] for a in range(3)],'slices':slices})
(P/'source_coordinates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_Original_Editable.blend'))
print('HIGHLAND_SOURCE_COORDINATES '+json.dumps([{k:v for k,v in r.items() if k!='slices'} for r in rows]),flush=True)
