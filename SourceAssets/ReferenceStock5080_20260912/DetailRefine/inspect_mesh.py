import bpy,bmesh,json,math
from pathlib import Path
R=Path(__file__).parent;result={}
for key in ['m4','akm']:
 bpy.ops.wm.open_mainfile(filepath=str(R/key/'Stock_Refined_Editable.blend'));o=bpy.data.objects['SM_SkeletonStock'];me=o.data;bm=bmesh.new();bm.from_mesh(me)
 box=(.54,.73,.655,.85) if key=='m4' else (.055,.053,.285,.092);uv=me.uv_layers[0];outside=0;metal_faces=0
 for f in me.polygons:
  if 'Metal' not in me.materials[f.material_index].name:continue
  metal_faces+=1
  for li in f.loop_indices:
   u,v=uv.data[li].uv;outside+=int(not(box[0]-1e-6<=u<=box[2]+1e-6 and box[1]-1e-6<=v<=box[3]+1e-6))
 result[key]={'uv_layers':len(me.uv_layers),'metal_faces':metal_faces,'metal_uv_corners_outside_inspected_region':outside,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_polygons':sum(f.calc_area()<1e-10 for f in bm.faces),'all_vertices_finite':all(math.isfinite(a) for v in me.vertices for a in v.co)}
 edges=[e for e in bm.edges if e.is_boundary];result[key]['boundary_total_length_cm']=sum(e.calc_length() for e in edges);result[key]['boundary_max_edge_cm']=max((e.calc_length() for e in edges),default=0)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);result[key]['boundary_after_micron_weld_probe']=sum(e.is_boundary for e in bm.edges)
 assert outside==0 and result[key]['all_vertices_finite'] and result[key]['zero_area_polygons']==0;bm.free()
(R/'topology_uv_report.json').write_text(json.dumps(result,indent=2));print('REFINED_UV_GEOMETRY_PASS',json.dumps(result))
