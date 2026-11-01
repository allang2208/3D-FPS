from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((OUT/'final_poses.json').read_text()).items()}
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'After';folder.mkdir(exist_ok=True);report={}
for f in (7,12,16,20,24,29,34,39,43,48,52,55):
 row=final['fire'][f];set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
 target=row['thumb_02_r'].translation
 for view,offset in [('side',(.23,-.12,.14)),('front',(.14,.12,.06))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.21
  s.render.filepath=str(folder/f'fire_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
 for stage,pose in [('before',clips['fire'][f]),('after',row)]:
  ps=points(pose);data={}
  mask=np.isin(dominant,[names.index(n) for n in names if n.endswith('_r') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))])
  ix=np.where(mask)[0][::3];hits=actual(pose,ps[ix],True)
  for part,ds in hits.items():
   if ds.min()<-.0003:data[part]={'penetration_mm':float(max(0,-ds.min())*1000),'points_over_1mm':int((ds<-.001).sum()),'bones':sorted(set(names[int(dominant[j])] for j,d in zip(ix,ds) if d<-.001))}
  report.setdefault(str(f),{})[stage]=data
(OUT/'contact_review.json').write_text(json.dumps(report,indent=2));print('M24_THUMB_SOURCE_REVIEW',json.dumps(report),flush=True)
