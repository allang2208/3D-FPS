from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
settings={'gentle':(0,6,-8,6,6),'upright':(0,10,-10,5,5),'neutral':(0,0,0,0,0),'compact':(0,2,0,8,8)}
ix=np.where(digit_masks['thumb'])[0][::3];tip_ix=np.where(dominant==names.index('thumb_03_r'))[0]
finger_ix=np.where(np.isin(dominant,[names.index(n) for n in names if n.endswith('_r') and n.startswith(('index_','middle_','ring_','pinky_'))]))[0]
report={}
for name,(x,y,z,mcp,ip) in settings.items():
 bases=[Q(x,y,z),Q(z=mcp),Q(z=ip)];worst=0.;nearest=1.;hits=[]
 for f in range(16,42):
  row=thumb(clips['fire'][f],bases);ps=points(row);result=actual(row,ps[ix],True)
  for part,ds in result.items():
   pen=max(0,-float(ds.min()))*1000;worst=max(worst,pen)
   if pen>1:hits.append({'frame':f,'part':part,'mm':round(pen,2)})
  ds=np.linalg.norm(ps[tip_ix][::3,None,:]-ps[finger_ix][None,::3,:],axis=2);nearest=min(nearest,float(ds.min()))
 report[name]={'basis':settings[name],'max_gun_penetration_mm':worst,'tip_to_other_fingers_vertex_distance_mm':nearest*1000,'hits':hits}
(OUT/'pose_candidates.json').write_text(json.dumps(report,indent=2));print('M24_THUMB_CANDIDATES',json.dumps(report),flush=True)
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Candidates';folder.mkdir(exist_ok=True)
for name,(x,y,z,mcp,ip) in settings.items():
 for f in (20,27,34):
  row=thumb(clips['fire'][f],[Q(x,y,z),Q(z=mcp),Q(z=ip)]);set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  target=(row['thumb_02_r'].translation+row['index_01_r'].translation)*.5
  for view,off in [('back',(.20,-.12,.14)),('palm',(.20,.14,.03))]:
   cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.18
   s.render.filepath=str(folder/f'{name}_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
