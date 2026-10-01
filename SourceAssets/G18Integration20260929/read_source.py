import bpy, json
from pathlib import Path
from mathutils import Vector
O = Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Original/G18/G18/FBX/G18_full.fbx'))
out=[]
for ob in bpy.context.scene.objects:
    row={'name':ob.name,'type':ob.type,'matrix':[list(x) for x in ob.matrix_world]}
    if ob.type=='MESH':
        vv=[ob.matrix_world@v.co for v in ob.data.vertices]
        row.update(vertices=len(vv),faces=len(ob.data.polygons),materials=[m.name if m else '' for m in ob.data.materials],groups=[g.name for g in ob.vertex_groups],min=[min(v[i] for v in vv) for i in range(3)],max=[max(v[i] for v in vv) for i in range(3)])
        neighbors={v.index:set() for v in ob.data.vertices}
        for e in ob.data.edges:
            a,b=e.vertices;neighbors[a].add(b);neighbors[b].add(a)
        remaining=set(neighbors);parts=[]
        while remaining:
            todo=[next(iter(remaining))];part=set()
            while todo:
                n=todo.pop()
                if n in part:continue
                part.add(n);todo.extend(neighbors[n]-part)
            remaining-=part
            parts.append({'count':len(part),'min':[min(vv[j][i] for j in part) for i in range(3)],'max':[max(vv[j][i] for j in part) for i in range(3)],'seed':min(part)})
        row['parts']=sorted(parts,key=lambda p:-p['count'])
    if ob.type=='ARMATURE':row['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in ob.data.bones]
    out.append(row)
(O/'source_geometry.json').write_text(json.dumps(out,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'G18_Original.blend'))
print(json.dumps(out))
