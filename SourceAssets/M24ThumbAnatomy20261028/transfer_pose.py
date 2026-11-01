from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
ix=np.where(digit_masks['thumb'])[0][::3];records={};poses={}
for f in (16,20,25,30,32,34,35,36,37,39,41):
 src=clips['fire'][f];records[str(f)]={}
 for mode in ('before','transfer','yminus25','yminus40'):
  if mode=='before':row=src
  else:
   if mode=='transfer':
    proximal=src['thumb_02_r'].to_quaternion();root_world=proximal@(local_rest['thumb_02_r'].to_quaternion()@Q(z=2)).inverted()
    root_basis=local_rest['thumb_01_r'].to_quaternion().inverted()@src['hand_r'].to_quaternion().inverted()@root_world
    bases=[root_basis,Q(z=2),Q(z=6)]
   else:bases=[Q(y=-25 if mode=='yminus25' else -40,z=40),Q(z=5),Q(z=6)]
   row=thumb(src,bases)
  ps=points(row);hits={}
  for part,ds in actual(row,ps[ix],True).items():
   if ds.min()<-.0005:hits[part]={'mm':round(float(-ds.min())*1000,2),'bones':sorted(set(names[int(dominant[i])] for i,d in zip(ix,ds) if d<-.0005))}
  records[str(f)][mode]={'hits':hits,'q1_xyz':[round(math.degrees(x),2) for x in (local_rest['thumb_01_r'].to_quaternion().inverted()@(row['hand_r'].inverted()@row['thumb_01_r']).to_quaternion()).to_euler('XYZ')]}
  poses[(f,mode)]=row
(OUT/'transfer_candidates.json').write_text(json.dumps(records,indent=2));print('M24_TRANSFER',json.dumps(records),flush=True)
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Transfer';folder.mkdir(exist_ok=True)
for f in (20,36):
 for mode in ('before','transfer','yminus25','yminus40'):
  row=poses[(f,mode)];set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  target=(row['thumb_02_r'].translation+row['index_01_r'].translation)*.5
  cam.location=target+Vector((.20,-.12,.14));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.18
  s.render.filepath=str(folder/f'{mode}_{f:03d}.png');bpy.ops.render.render(write_still=True)
