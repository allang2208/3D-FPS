from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((O/'final_poses.json').read_text()).items()}
setup_render();s.render.resolution_x=800;s.render.resolution_y=450
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
node=next(n for n in ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full')
exec(compile(ast.unparse(node),'morphs','exec'))
view=Matrix(((0,.01,0,0),(.01,0,0,0),(0,0,.01,0),(0,0,0,1)))@C
base=bpy.data.objects['M24_clip'];ext=bpy.data.objects['M24_Magazine10']
for name in ('M24_silencer','M24_ExtraScope_Lowpoly','M24_Laser_Lowpoly','M24_LaserHolder_Lowpoly','M24_bullet'):bpy.data.objects[name].hide_render=True
folder=O/'Review';folder.mkdir(exist_ok=True);measure={}
for role in ('reload','reload_mag10'):
 extended=role.endswith('_mag10');obj=ext if extended else base;bounds=[Vector(v) for v in obj.bound_box];measure[role]={'reset_visible_samples':[],'samples':[]}
 for f in (20,22,23.5,24.5,25.25,26,27,29,29.5,30,31,33,35,38,40,42,46,50):
  row=final[role][round(f*4)];set_pose(row);morphs_full();r.matrix_world=view
  base.hide_render=extended;ext.hide_render=not extended;ext.matrix_world=view@row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
  cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
  s.render.filepath=str(folder/(role+'_'+str(f)+'.png'));bpy.ops.render.render(write_still=True)
  measure[role]['samples'].append({'frame':f,'hand_cm':list(C@row['hand_l'].translation),'magazine_cm':list(C@row['WPN_Magazine'].translation)})
 for k in range(29*4,30*4+1):
  row=final[role][k];M=C@row['WPN_Magazine']@rest['WPN_Magazine'].inverted();pts=[M@v for v in bounds]
  # Every vertex must be below the lower frustum plane during the prop role switch.
  margin=max(p.z+p.x*math.tan(math.radians(37.5)) for p in pts)
  measure[role]['reset_visible_samples'].append({'frame':k/4,'top_margin_cm':margin})
 for f in (24.5,25.25,26,35,40,42):
  row=final[role][round(f*4)];r.matrix_world=Matrix.Identity(4);set_pose(row);morphs_full();ext.matrix_world=row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
  target=(row['hand_l'].translation+row['middle_02_l'].translation)*.5;cam.location=target+Vector((-.30,-.12,.10));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.29
  s.render.filepath=str(folder/(role+'_'+str(f)+'_hand.png'));bpy.ops.render.render(write_still=True)
(O/'review_geometry.json').write_text(json.dumps(measure,indent=2));print('M24_FLOW_REVIEW_RENDERED',flush=True)
