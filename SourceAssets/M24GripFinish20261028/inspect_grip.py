from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
base=clone(clips['idle'][0]);native=clone(base)
native.update(raw_hand(base,1));fixed_arm(native,'r',0.)
rows={'current':base,'donor':native}
for name,row in rows.items():
 d=actual(row,points(row)[hm][::3],True,{'M24_base'})['M24_base']
 print(name,'HAND_MM',float(d.min()*1000),'inside',int((d<-.001).sum()),'WRIST',list(row['hand_r'].translation),flush=True)
(OUT/'grip_candidates.json').write_text(json.dumps({n:serial([v])[0] for n,v in rows.items()}))
# Local surface views, using the existing camera calibration without edits.
code=(OUT.parent/'M24ArmRebuild20261027/preview.py').read_text()
code=code[code.index('def angle'):code.index('for name,role,f,view in ')]
exec(compile(code,'render_setup','exec'))
r.animation_data_clear()
for name,row in rows.items():
 for n,m in row.items():
  loc=row[parents[n]].inverted()@m if parents[n] else m
  r.pose.bones[n].matrix_basis=local_rest[n].inverted()@loc
 bpy.context.view_layer.update();morphs();r.matrix_world=Matrix.Identity(4)
 target=row['hand_r'].translation+Vector((0,0,.02))
 for view,offset in [('side',(.27,-.13,.18)),('palm',(-.22,-.15,-.10))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.25
  s.render.filepath=str(OUT/(name+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
