from pathlib import Path
exec(compile((Path(__file__).parent/'review_pose.py').read_text().split('metrics=[];')[0],'review_setup','exec'))
set_pose(rest,0);deps=bpy.context.evaluated_depsgraph_get()
for n in ('M24_base','M24_barrel','M24_V9_BareArms'):
 ob=bpy.data.objects.get(n)
 if not ob:continue
 ev=ob.evaluated_get(deps);me=ev.to_mesh();points=[ev.matrix_world@v.co for v in me.vertices]
 print(n,'bounds',[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],flush=True)
 if n=='M24_base':
  tree=BVHTree.FromPolygons(points,[tuple(f.vertices) for f in me.polygons])
  for y in (.32,.37,.42,.47,.55,.61):
   hits=[]
   for x in (0,.014,.023,.032):
    low=tree.ray_cast(Vector((x,y,-1)),Vector((0,0,1)),2)[0];high=tree.ray_cast(Vector((x,y,1)),Vector((0,0,-1)),2)[0]
    hits.append((x,list(low) if low else None,list(high) if high else None))
   print('rays',y,hits,flush=True)
 for y in (.37,.42,.47,.55,.61):
  pts=[p for p in points if abs(p.y-y)<.015]
  if pts:print('slice',y,[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in (0,2)],flush=True)
 ev.to_mesh_clear()
print('MESHLIST',[(o.name,o.hide_render) for o in bpy.data.objects if o.type=='MESH'],flush=True)
for ob in parts:
 points=[ob.matrix_world@v.co for v in ob.data.vertices]
 print('PART_BOUNDS',ob.name,[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],flush=True)
idle=sample_pose(0);native_frame=rest['WPN_root']@idle['WPN_root'].inverted()
print('ARM_NATIVE', {n:list((native_frame@idle[n]).translation) for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','index_01_l','index_03_l','middle_03_l','pinky_03_l')},flush=True)
