import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent
R=Matrix(json.loads((S/'HK416Reworked20260930/authoring.json').read_text())['root_matrix'])
bpy.ops.wm.read_factory_settings(use_empty=True)
report={}
for key in ['phantom_reargrip','stable_antislip_reargrip','balanced_reargrip']:
    file=S/'HK416CommonAttachments20260930/Meshes'/('SM_HK416_'+key+'.blend')
    with bpy.data.libraries.load(str(file),link=False) as (a,b):b.objects=a.objects
    ob=next(o for o in b.objects if o.type=='MESH');ob.data.transform(R.inverted()@ob.matrix_world);ob.data.update()
    rows={}
    for z in [0,.008]:
        bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        print(key,z,'original_open_edges',sum(e.is_boundary for e in bm.edges),flush=True)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,z),plane_no=(0,0,1),clear_outer=True)
        rim=[v for v in bm.verts if abs(v.co.z-z)<1e-6]
        for v in rim:v.co.z=z
        bmesh.ops.remove_doubles(bm,verts=rim,dist=1e-5)
        edges=set(e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<1e-7 for v in e.verts));components=[]
        while edges:
            todo=[edges.pop()];es=[]
            while todo:
                e=todo.pop();es.append(e)
                for v in e.verts:
                    for n in v.link_edges:
                        if n in edges:edges.remove(n);todo.append(n)
            vs=set(v for e in es for v in e.verts)
            components.append({'edges':len(es),'bounds':[[round(min(v.co[i] for v in vs)*1000,3),round(max(v.co[i] for v in vs)*1000,3)] for i in (0,1)],'degrees':sorted(set(sum(e in es for e in v.link_edges) for v in vs)),'slots':sorted(set(f.material_index for e in es for f in e.link_faces))})
        rows[z]=components;bm.free()
    report[key]=rows
(O/'sections.json').write_text(json.dumps(report,indent=2))
for key,rows in report.items():
    print(key,flush=True)
    for z,comps in rows.items():
        print(z,'components',len(comps),'largest',sorted(comps,key=lambda c:-c['edges'])[:3],flush=True)
