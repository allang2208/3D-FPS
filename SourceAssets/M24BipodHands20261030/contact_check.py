from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
groups={g.index:g.name for g in skin.vertex_groups}
selected=[v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if under(groups.get(g.group,''),'hand_l'))>.6]
report=[]
for t in sorted(set([i/1000 for i in range(35,116,5)]+[.12,.15,.18,.21,.24,.27,.30,.33,.36,.4])):
    row=sample_pose(t);set_pose(row,t);deps=bpy.context.evaluated_depsgraph_get()
    vertices=[];faces=[]
    for ob in parts:
        ev=ob.evaluated_get(deps);me=ev.to_mesh();offset=len(vertices)
        vertices.extend(ev.matrix_world@v.co for v in me.vertices);faces.extend(tuple(offset+i for i in p.vertices) for p in me.polygons);ev.to_mesh_clear()
    tree=BVHTree.FromPolygons(vertices,faces);ev=skin.evaluated_get(deps);me=ev.to_mesh();inside=[];by_bone={};min_distance=1.
    for i in selected:
        p=ev.matrix_world@me.vertices[i].co;hit=tree.find_nearest(p)
        if hit[0] is None:continue
        min_distance=min(min_distance,hit[3])
        if hit[3]>.015 or (p-hit[0]).dot(hit[1])>=-.0015:continue
        votes=0
        for direction in (Vector((1,.037,.019)).normalized(),Vector((.031,1,.017)).normalized(),Vector((.029,.023,1)).normalized()):
            count=0;origin=p.copy()
            for k in range(16):
                loc,normal,idx,dist=tree.ray_cast(origin,direction,1.)
                if loc is None:break
                count+=1;origin=loc+direction*.00001
            votes+=count%2
        if votes>=2:
            inside.append(hit[3]*1000);bone=groups[max(skin.data.vertices[i].groups,key=lambda g:g.weight).group];by_bone[bone]=by_bone.get(bone,0)+1
    ev.to_mesh_clear();report.append({'time':t,'inside_vertices':len(inside),'max_depth_mm':max(inside,default=0.),'contact_gap_mm':min_distance*1000,'bones':by_bone})
(folder/'hand_contact.json').write_text(json.dumps(report,indent=2));print('CONTACT',json.dumps(report),flush=True)
