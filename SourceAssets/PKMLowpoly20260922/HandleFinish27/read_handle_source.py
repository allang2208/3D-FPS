"""Read the current carry assembly for local mesh authoring; no rendering."""
import bpy, json
from pathlib import Path
from mathutils import Matrix, Vector

O = Path(__file__).parent
R = O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'), use_scripts=False)
rig = bpy.data.objects['PKM_Manny_Rig']
rig.data.pose_position = 'REST'
fit = Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
gun_inv = (rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local @ fit).inverted()
wood = bpy.data.objects['PKM_Part_136']
pts = [gun_inv @ wood.matrix_world @ v.co for v in wood.data.vertices]
center = sum(pts, Vector())/len(pts)
out = {}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not obj.name.startswith('PKM_Part_'):
        continue
    pts = [gun_inv @ obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    if not (lo.x < .11 and hi.x > .035 and lo.y < .06 and hi.y > -.07 and lo.z < .15 and hi.z > .08):
        continue
    adj = {v.index:set() for v in obj.data.vertices}
    for edge in obj.data.edges:
        a,b = edge.vertices; adj[a].add(b); adj[b].add(a)
    unseen = set(adj); islands=[]
    while unseen:
        stack=[unseen.pop()]; group=[]
        while stack:
            v=stack.pop();group.append(v)
            connected=adj[v]&unseen;unseen-=connected;stack.extend(connected)
        islands.append({'count':len(group), 'indices':group,
            'min':[min(pts[i][j] for i in group) for j in range(3)],
            'max':[max(pts[i][j] for i in group) for j in range(3)]})
    row={'min':list(lo),'max':list(hi),'vertices':[list(p) for p in pts],
         'faces':[list(p.vertices) for p in obj.data.polygons],
         'materials':[m.name for m in obj.data.materials],
         'mechanical_bone':obj.get('mechanical_bone'),
         'groups':[g.name for g in obj.vertex_groups], 'islands':islands}
    out[obj.name]=row
    print('HANDLE_PART', obj.name, row['mechanical_bone'], list(lo), list(hi),
          [(c['count'],c['min'],c['max']) for c in islands], flush=True)
(O/'handle_geometry.json').write_text(json.dumps(out,indent=2))
