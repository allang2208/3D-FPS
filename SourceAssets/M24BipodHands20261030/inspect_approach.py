from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
t=.055;row=sample_pose(t);set_pose(row,t);deps=bpy.context.evaluated_depsgraph_get();root=row['WPN_root']@rest['WPN_root'].inverted()
vertices=[];faces=[]
for ob in parts:
    ev=ob.evaluated_get(deps);me=ev.to_mesh();off=len(vertices);vertices.extend(ev.matrix_world@v.co for v in me.vertices);faces.extend(tuple(off+i for i in p.vertices) for p in me.polygons);ev.to_mesh_clear()
tree=BVHTree.FromPolygons(vertices,faces);ev=skin.evaluated_get(deps);me=ev.to_mesh();groups={g.index:g.name for g in skin.vertex_groups};bad=[]
for v in skin.data.vertices:
    bone=groups[max(v.groups,key=lambda g:g.weight).group]
    if not bone.startswith('index_') or not bone.endswith('_l'):continue
    p=ev.matrix_world@me.vertices[v.index].co;hit=tree.find_nearest(p)
    if hit[0] is not None and hit[3]<.015 and (p-hit[0]).dot(hit[1])<-.001:
        bad.append({'depth_mm':hit[3]*1000,'bone':bone,'normal_native':list(root.to_quaternion().inverted()@hit[1]),'p_native':list(root.inverted()@p)})
print('APPROACH_WORST',json.dumps(sorted(bad,key=lambda a:-a['depth_mm'])[:5]),flush=True)
ev.to_mesh_clear()
target=row['hand_l'].translation+root.to_3x3()@Vector((.015,.025,.01));cam.location=target+root.to_3x3()@Vector((-.26,.06,.18));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.25
s.render.resolution_x=640;s.render.resolution_y=400;s.render.filepath=str(folder/'approach_current.png');bpy.ops.render.render(write_still=True)
