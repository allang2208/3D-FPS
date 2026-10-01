import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent/'G18Integration20260929';R={}
bpy.ops.wm.open_mainfile(filepath=str(S/'Single/G18_single_Editable.blend'))
rig=bpy.data.objects['SK_G18_Manny'];inv=rig.data.bones['WPN_root'].matrix_local.inverted()
mag=bpy.data.objects['G18_G18_mag'];body=bpy.data.objects['G18_G18']
bm=bmesh.new();bm.from_mesh(mag.data)
for v in bm.verts:v.co=inv@v.co
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bm.verts.ensure_lookup_table();remaining=set(bm.verts);components=[]
while remaining:
    stack=[remaining.pop()];part=[]
    while stack:
        v=stack.pop();part.append(v)
        for e in v.link_edges:
            w=e.other_vert(v)
            if w in remaining:remaining.remove(w);stack.append(w)
    components.append({'count':len(part),'lo':[min(v.co[i] for v in part) for i in range(3)],'hi':[max(v.co[i] for v in part) for i in range(3)],'open_edges':len({e for v in part for e in v.link_edges if e.is_boundary})})
R['magazine']={'parts':components,'open_edges':[[list(v.co) for v in e.verts] for e in bm.edges if e.is_boundary]}
coords=[inv@v.co for v in body.data.vertices];tree=BVHTree.FromPolygons(coords,[list(p.vertices) for p in body.data.polygons])
R['slide_roof']=[]
for y in (.025,.035,.045,.055,.065):
    for x in (-.013,-.010,-.006,0,.006,.010,.013):
        hit=tree.ray_cast(Vector((x,y,.10)),Vector((0,0,-1)))[0]
        R['slide_roof'].append([x,y,hit.z if hit else None])
for key in ('holographic','panoramic_red_dot'):
    bpy.ops.wm.open_mainfile(filepath=str(S/f'Attachments/SM_G18_{key}_Editable.blend'))
    ob=bpy.data.objects['SM_G18_'+key];by_material={}
    for p in ob.data.polygons:
        name=ob.data.materials[p.material_index].name
        by_material.setdefault(name,[]).extend([list(ob.matrix_world@ob.data.vertices[i].co) for i in p.vertices])
    R[key]={'materials':{n:{'lo':[min(v[i] for v in vs) for i in range(3)],'hi':[max(v[i] for v in vs) for i in range(3)],'faces':len(vs)} for n,vs in by_material.items()},'matrix':[list(row) for row in ob.matrix_world],'sockets':{c.name:list(c.location) for c in ob.children if c.type=='EMPTY'}}
    ob.data.calc_loop_triangles();v=[ob.matrix_world@p.co for p in ob.data.vertices]
    mask={i for i,m in enumerate(ob.data.materials) if 'adapter' not in m.name.lower() and 'g18_attachmentfinish' not in m.name.lower() and not any(k in m.name.lower() for k in ('glass','reticle'))}
    ts=[list(t.vertices) for t in ob.data.loop_triangles if t.material_index in mask];bvh=BVHTree.FromPolygons(v,ts,all_triangles=True)
    R[key]['underside']=[]
    for x in (-.014,-.009,-.004,.001,.006,.011,.016):
        for y in (-.010,-.005,0,.005,.010):
            hit=bvh.ray_cast(Vector((x,y,-.1)),Vector((0,0,1)))[0]
            R[key]['underside'].append([x,y,hit.z if hit else None])
(O/'source_shape.json').write_text(json.dumps(R,indent=2))
print('G18_REPAIR_SOURCE_DIMENSIONS_WRITTEN',flush=True)
