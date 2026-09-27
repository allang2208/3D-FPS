import bpy,bmesh,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'BranchCrystalV18/Staff_BranchCrystal_V18.blend'))
report={}
for name in ('Meshy_OriginalMaster','AuthoredBranchShaft','SM_Staff_Body','SM_Staff_head_crystal_false','SM_Staff_grip_lining_false'):
    obj=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(obj.data)
    row={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_before_weld':sum(e.is_boundary for e in bm.edges)}
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    boundaries=[e for e in bm.edges if e.is_boundary]
    row.update({'welded_vertices':len(bm.verts),'boundary_after_weld':len(boundaries),
        'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
        'degenerate_faces':sum(f.calc_area()<1e-8 for f in bm.faces)})
    wood=[];outward=[];inward=[]
    for face in bm.faces:
        center=face.calc_center_median()
        if -75<center.z<54 and center.xy.length>1.2 and abs(face.normal.z)<.9:
            dot=face.normal.x*center.x+face.normal.y*center.y
            (outward if dot>=0 else inward).append(face.calc_area())
    row['outward_side_area']=sum(outward);row['inward_side_area']=sum(inward)
    unvisited=set(boundaries);loops=[]
    while unvisited:
        work=[unvisited.pop()];edges=[]
        while work:
            edge=work.pop();edges.append(edge)
            for v in edge.verts:
                for e in v.link_edges:
                    if e in unvisited:unvisited.remove(e);work.append(e)
        loops.append({'edges':len(edges),'z_min':min(v.co.z for e in edges for v in e.verts),'z_max':max(v.co.z for e in edges for v in e.verts)})
    row['largest_open_boundaries']=sorted(loops,key=lambda x:x['edges'],reverse=True)[:8]
    report[name]=row;bm.free()
(ROOT/'before_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
