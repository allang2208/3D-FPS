"""Extract the donor loader handle and binding for the five-pocket adapter."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'RSH12Integration20261003/Donor/single/SK_DW715_Donor.fbx'))
r=next(o for o in bpy.data.objects if o.type=='ARMATURE');bone=r.data.bones['WPN_Loader'];parts=[]
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    group=ob.vertex_groups.get('WPN_Loader')
    if not group:continue
    ids={v.index for v in ob.data.vertices if any(g.group==group.index and g.weight>.5 for g in v.groups)}
    if not ids:continue
    m=bone.matrix_local.inverted()@r.matrix_world.inverted()@ob.matrix_world
    v=[m@p.co for p in ob.data.vertices];faces=[list(p.vertices) for p in ob.data.polygons if all(i in ids for i in p.vertices)]
    adjacency={i:set() for i in ids}
    for f in faces:
        for i in f:adjacency[i].update(f)
    shells=[];seen=set()
    for i in ids:
        if i in seen:continue
        stack=[i];seen.add(i);s=[]
        while stack:
            j=stack.pop();s.append(j)
            for k in adjacency[j]:
                if k not in seen:seen.add(k);stack.append(k)
        shells.append(dict(ids=s,min=[min(v[j][a] for j in s) for a in range(3)],max=[max(v[j][a] for j in s) for a in range(3)]))
    parts.append(dict(name=ob.name,verts=[list(p) for p in v],faces=faces,shells=shells))
(O/'donor_loader_geometry.json').write_text(json.dumps(parts,separators=(',',':')))
pts=[r.data.bones['WPN_root'].matrix_local.inverted()@bone.matrix_local@Vector(p['verts'][i]) for p in parts for s in p['shells'] for i in s['ids']]
print('DONOR_LOADER_GUN_BOUNDS',[[min(v[a] for v in pts),max(v[a] for v in pts)] for a in range(3)],flush=True)
print('DONOR_CYLINDER',list((r.data.bones['WPN_root'].matrix_local.inverted()@r.data.bones['WPN_Cylinder'].matrix_local).translation),flush=True)
