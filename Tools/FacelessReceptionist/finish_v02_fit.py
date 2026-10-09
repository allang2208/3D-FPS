from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist\author_character_v02.py')
s=p.read_text(encoding='utf-8')
s=s.replace("if p.z<1.16 and abs(p.x)<.26:arm_blend=0.","if p.z<1.16 and abs(p.x)<.215:arm_blend=0.")
s=s.replace("if p.z>1.548 and abs(p.x)<.085:return False","if p.z>1.54 and math.hypot(p.x,p.y-.005)<.058+(p.z-1.54)*2.:return False")
# Keep cloth layers together while correcting rest-space clearance; moving both
# shell vertices equally preserves the physical 2.8/1.5 mm thickness.
needle="bind(body,body_weights)\n# Retain"
replacement="""bind(body,body_weights)
body.data.calc_loop_triangles()
rest_points=[v.co.copy() for v in body.data.vertices]
rest_tris=[tuple(t.vertices) for t in body.data.loop_triangles]
rest_bvh=BVHTree.FromPolygons(rest_points,rest_tris,all_triangles=True)
for o in parts:
 if o.name not in ['Receptionist_Blazer_Continuous','Receptionist_Shirt_Continuous']:continue
 count=len(o.data.vertices)//2
 clearance=.009 if 'Blazer' in o.name else .003
 for i in range(count):
  v=o.data.vertices[i];h=rest_bvh.find_nearest(v.co)
  if h[0] is None:continue
  signed=(v.co-h[0]).dot(h[1])
  if signed<clearance:
   delta=h[1]*(clearance-signed)
   v.co+=delta;o.data.vertices[i+count].co+=delta
 o.data.update();o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
# Retain"""
s=s.replace(needle,replacement)
p.write_text(s,encoding='utf-8')
