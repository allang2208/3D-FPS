from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((OUT/'final_poses.json').read_text()).items()}
ix=np.where(digit_masks['thumb'])[0][::3];report={'before':{},'after':{},'unowned_matrix_delta':0.,'max_local_translation_delta_mm':0.,'source_review_only':True}
for role,rows in final.items():
 for f,row in enumerate(rows):
  old=clips[role][f]
  report['unowned_matrix_delta']=max(report['unowned_matrix_delta'],max(max(abs(row[n][i][j]-old[n][i][j]) for i in range(4) for j in range(4)) for n in names if n not in thumb_names))
  for n in thumb_names:
   a=row[parents[n]].inverted()@row[n];b=old[parents[n]].inverted()@old[n]
   report['max_local_translation_delta_mm']=max(report['max_local_translation_delta_mm'],(a.translation-b.translation).length*1000)
for f in range(7,53):
 for stage,row in [('before',clips['fire'][f]),('after',final['fire'][f])]:
  hits={}
  for part,ds in actual(row,points(row)[ix],True).items():
   if ds.min()<-.001:hits[part]={'mm':round(float(-ds.min())*1000,2),'bones':sorted(set(names[int(dominant[i])] for i,d in zip(ix,ds) if d<-.001))}
  if hits:report[stage][str(f)]=hits
(OUT/'source_review.json').write_text(json.dumps(report,indent=2));print('M24_THUMB_ANATOMY_REVIEW',json.dumps(report),flush=True)
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'FinalReview';folder.mkdir(exist_ok=True)
for f in (7,20,27,34,36,43):
 for stage,rows in [('before',clips['fire']),('after',final['fire'])]:
  row=rows[f];set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  for ob in s.objects:
   if ob.type=='MESH' and ob!=skin:ob.hide_render=False
  target=(row['thumb_02_r'].translation+row['index_01_r'].translation)*.5
  for view,off in [('back',(.20,-.12,.14)),('palm',(.20,.14,.03))]:
   cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.18
   s.render.filepath=str(folder/f'{stage}_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
  for ob in s.objects:
   if ob.type=='MESH' and ob!=skin:ob.hide_render=True
  frame=row['hand_r'].to_3x3()@rest['hand_r'].to_3x3().inverted()@target_frame;target=row['hand_r'].translation+frame.col[0]*.065
  cam.location=target-frame.col[2]*.30+frame.col[1]*.04;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.22
  s.render.filepath=str(folder/f'{stage}_{f:03d}_study.png');bpy.ops.render.render(write_still=True)
