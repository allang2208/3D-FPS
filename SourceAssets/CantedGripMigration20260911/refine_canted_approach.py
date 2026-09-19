import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
source=(O/'refine_canted_surface.py').read_text().split('for xyz in')[0];exec(compile(source,str(O/'approach_generated.py'),'exec'))
from audit_m4 import support
code=(O/'build_akm.py').read_text();exec(code[code.index('def arm('):code.index('def render(')],globals());reports={}
for angle in [35,45,55]:
 p={n:m.copy() for n,m in old.items()};R=B@Matrix.Rotation(math.radians(angle),4,'Z')@B.inverted()
 for n in p:
  if n=='hand_l' or n.endswith('_l') and n.startswith(tuple(digits)):p[n]=R@p[n]
 H=p['hand_l'];A=p['upperarm_l'].translation;l1=(p['lowerarm_l'].translation-A).length;l2=(old['hand_l'].translation-old['lowerarm_l'].translation).length;desired=H.to_3x3()@rest['hand_l'].to_3x3().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized();E=H.translation-desired*l2;delta=(E+(A-E).normalized()*l1-A)*.7
 # Solve from the unmodified source segment lengths and the new palm target.
 for n in ['hand_l']:p[n]=old[n].copy()
 metric=arm(p,rest,H,1,delta)
 for n in p:
  if n.endswith('_l') and n.startswith(tuple(digits)):p[n]=R@old[n]
 apply(r,p,rest);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];hit=len(BVHTree.FromPolygons(v,faces,all_triangles=True).overlap(tree));e.to_mesh_clear();metric['grip_pairs']=hit;metric['elbow_in_grip']=list(G.inverted()@p['lowerarm_l'].translation);reports[angle]=metric;render(r,G,'approach_'+str(angle));print('APPROACH',angle,metric,flush=True)
 if angle==55:
  f['hand_in_root']=[list(x) for x in p['WPN_root'].inverted()@H];f['shoulder_in_grip']=list(G.inverted()@p['upperarm_l'].translation);f['approach_azimuth_deg']=angle;f['basis']={n:[list(x) for x in r.pose.bones[n].matrix_basis] for n in f['basis']};(O/'canted_refit.json').write_text(json.dumps(f,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'Canted_Refit.blend'))
(O/'approach_audit.json').write_text(json.dumps(reports,indent=2))
