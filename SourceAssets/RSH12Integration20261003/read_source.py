"""Read the actual FBX into an editable source scene and record authoring geometry."""
import bpy, json
from pathlib import Path
from mathutils import Vector
O = Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Original/Extracted/source/Rsh-12.fbx'))
parts=[]
for ob in bpy.data.objects:
    if ob.type != 'MESH': continue
    vv=[ob.matrix_world@v.co for v in ob.data.vertices]
    adj=[set() for _ in vv]
    for e in ob.data.edges:
        a,b=e.vertices;adj[a].add(b);adj[b].add(a)
    seen=set();shells=[]
    for i in range(len(vv)):
        if i in seen: continue
        stack=[i];seen.add(i);ids=[]
        while stack:
            a=stack.pop();ids.append(a)
            for b in adj[a]:
                if b not in seen:seen.add(b);stack.append(b)
        shells.append(dict(ids=ids,min=[min(vv[i][a] for i in ids) for a in range(3)],max=[max(vv[i][a] for i in ids) for a in range(3)]))
    parts.append(dict(name=ob.name,vertices=len(vv),triangles=sum(len(p.vertices)-2 for p in ob.data.polygons),
        matrix=[list(row) for row in ob.matrix_world],min=[min(v[a] for v in vv) for a in range(3)],
        max=[max(v[a] for v in vv) for a in range(3)],materials=[m.name if m else '' for m in ob.data.materials],shells=shells))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'RSH12_Original.blend'))
(O/'source_geometry.json').write_text(json.dumps(dict(parts=parts),indent=2),encoding='utf-8')
for p in parts:
    print('SOURCE_PART',p['name'],p['vertices'],p['triangles'],p['min'],p['max'], 'shells', len(p['shells']), flush=True)
base=bpy.data.objects['1_l'].matrix_world
axes=__import__('mathutils').Matrix(((0,0,1,0),(1,0,0,0),(0,1,0,0),(0,0,0,1)))
canonical=[]
for ob in bpy.data.objects:
    if ob.type!='MESH' or '.' in ob.name:continue
    m=__import__('mathutils').Matrix.Diagonal((.001,.001,.001,1))@axes@base.inverted()@ob.matrix_world
    vv=[m@v.co for v in ob.data.vertices]
    canonical.append(dict(name=ob.name,verts=[list(v) for v in vv],faces=[list(p.vertices) for p in ob.data.polygons],
        uv=[list(v.uv) for v in ob.data.uv_layers.active.data],normals=[list((m.to_3x3().inverted().transposed()@n.vector).normalized()) for n in ob.data.corner_normals]))
    print('CANONICAL',ob.name,[round(min(v[a] for v in vv),5) for a in range(3)],[round(max(v[a] for v in vv),5) for a in range(3)],flush=True)
(O/'canonical_parts.json').write_text(json.dumps(canonical,separators=(',',':')),encoding='utf-8')
