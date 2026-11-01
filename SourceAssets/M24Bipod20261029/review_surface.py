from pathlib import Path
exec(compile((Path(__file__).parent/'review_pose.py').read_text().split('metrics=[];')[0],'review_setup','exec'))
checks=[]
groups={g.index:g.name for g in skin.vertex_groups}
selected=[v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if groups.get(g.group,'').endswith('_l') and (under(groups[g.group],'hand_l') or groups[g.group]=='lowerarm_l'))>.5]
for t in (0,.32,.45,.65,.85,1.02,1.20,1.40,1.60,1.78,1.92,2.05):
 row=sample_pose(t);set_pose(row,t);deps=bpy.context.evaluated_depsgraph_get();vertices=[];faces=[]
 for ob in bpy.data.objects:
  if ob.type!='MESH' or ob.hide_render or not ob.name.startswith('M24_') or ob==skin:continue
  ev=ob.evaluated_get(deps);me=ev.to_mesh();offset=len(vertices);vertices.extend(ev.matrix_world@v.co for v in me.vertices);faces.extend(tuple(offset+i for i in p.vertices) for p in me.polygons);ev.to_mesh_clear()
 tree=BVHTree.FromPolygons(vertices,faces);ev=skin.evaluated_get(deps);me=ev.to_mesh();depth=[]
 for i in selected:
  p=ev.matrix_world@me.vertices[i].co;hit=tree.find_nearest(p)
  if hit[0] is not None and hit[3]<.025 and (p-hit[0]).dot(hit[1])<-.0015:depth.append(hit[3]*1000)
 extra={}
 for kind in ('Base','Leg'):
  pv=[];pf=[]
  for ob in parts:
   if '_'+kind not in ob.name:continue
   evaluated=ob.evaluated_get(deps);part_mesh=evaluated.to_mesh();offset=len(pv);pv.extend(evaluated.matrix_world@v.co for v in part_mesh.vertices);pf.extend(tuple(offset+i for i in face.vertices) for face in part_mesh.polygons);evaluated.to_mesh_clear()
  part_tree=BVHTree.FromPolygons(pv,pf);hits=[];solid=[];by_bone={}
  for i in selected:
   p=ev.matrix_world@me.vertices[i].co;hit=part_tree.find_nearest(p)
   if hit[0] is not None and hit[3]<.02 and (p-hit[0]).dot(hit[1])<-.002:
    hits.append(hit[3]*1000);votes=0
    for direction in (Vector((1,.037,.019)).normalized(),Vector((.031,1,.017)).normalized(),Vector((.029,.023,1)).normalized()):
     count=0;origin=p.copy()
     for k in range(20):
      loc,normal,idx,dist=part_tree.ray_cast(origin,direction,1.)
      if loc is None:break
      count+=1;origin=loc+direction*.00001
     votes+=count%2
    if votes>=2:
     solid.append(hit[3]*1000);g=max(skin.data.vertices[i].groups,key=lambda g:g.weight);bone=groups[g.group];by_bone[bone]=by_bone.get(bone,0)+1
  extra[kind]={'suspected_vertices':len(hits),'max_depth_mm':max(hits,default=0),'inside_solid_vertices':len(solid),'inside_solid_depth_mm':max(solid,default=0),'bones':by_bone}
 ev.to_mesh_clear();checks.append({'t':t,'suspected_penetrating_vertices':len(depth),'max_near_surface_depth_mm':max(depth,default=0),'attachment_contacts':extra})
 if t in (0,.45,.85,1.20,1.40,1.60,1.78,1.92,2.05):
  target=row['hand_l'].translation+Vector((0,.025,.01));cam.location=target+Vector((.32,.08,.16));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.25
  s.render.filepath=str(folder/(f'{t:.3f}_inner.png'));bpy.ops.render.render(write_still=True)
(folder/'surface.json').write_text(json.dumps(checks,indent=2));print('M24_BIPOD_SURFACE',json.dumps(checks),flush=True)
