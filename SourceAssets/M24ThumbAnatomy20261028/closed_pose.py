from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
settings={'cup_a':(0,6,30,10,10),'cup_b':(10,-6,35,14,12),'cup_c':(12,6,42,16,12),'cup_d':(0,-12,45,10,10),'cup_e':(15,12,30,22,18),'cup_f':(-10,10,40,18,12)}
ix=np.where(digit_masks['thumb'])[0][::3];report={}
for name,(x,y,z,mcp,ip) in settings.items():
 bases=[Q(x,y,z),Q(z=mcp),Q(z=ip)];hits=[]
 for f in (20,30,32,34,35,36,37,39):
  row=thumb(clips['fire'][f],bases);ps=points(row);result=actual(row,ps[ix],True)
  for part,ds in result.items():
   pen=max(0,-float(ds.min()))*1000
   if pen>.5:hits.append({'frame':f,'part':part,'mm':round(pen,2)})
 report[name]={'basis':settings[name],'hits':hits}
(OUT/'closed_candidates.json').write_text(json.dumps(report,indent=2));print('M24_CLOSED_POSE',json.dumps(report),flush=True)
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
exec(compile(code[code.index('def angle'):code.index('for name,role,f,view in ')],'render_setup','exec'))
folder=OUT/'Closed';folder.mkdir(exist_ok=True)
for name,(x,y,z,mcp,ip) in settings.items():
 for f in (20,36):
  row=thumb(clips['fire'][f],[Q(x,y,z),Q(z=mcp),Q(z=ip)]);set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  target=(row['thumb_02_r'].translation+row['index_01_r'].translation)*.5
  for view,off in [('back',(.20,-.12,.14)),('palm',(.20,.14,.03))]:
   cam.location=target+Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.18
   s.render.filepath=str(folder/f'{name}_{f:03d}_{view}.png');bpy.ops.render.render(write_still=True)
