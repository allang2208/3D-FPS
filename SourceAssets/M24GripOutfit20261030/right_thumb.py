from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
base=pose('idle',0)[0];set_pose(base);rt=base['WPN_root']@rest['WPN_root'].inverted()
out={}
for n in ('hand_r','thumb_01_r','thumb_02_r','thumb_03_r','index_01_r','index_03_r'):
    loc=base[parents[n]].inverted()@base[n];out[n]={'source':list(rt.inverted()@base[n].translation),'basis_deg':[math.degrees(v) for v in (local_rest[n].inverted()@loc).to_euler()]}
for mode,off in [('side',(.22,-.13,.12)),('back',(-.22,-.13,.12))]:
    r.matrix_world=Matrix.Identity(4);advanced.matrix_world=rt@advanced_rest;target=base['thumb_02_r'].translation;cam.location=target+rt.to_3x3()@Vector(off);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.20
    s.render.filepath=str(O/'Diagnosis'/('right_thumb_'+mode+'.png'));bpy.ops.render.render(write_still=True)
(O/'right_thumb.json').write_text(json.dumps(out,indent=2));print('RIGHT_THUMB',json.dumps(out),flush=True)
