from pathlib import Path
exec(compile((Path(__file__).parent/'author_profiles.py').read_text().split('report={};previews={};modified={}')[0],'setup','exec'))
new=json.loads((O/'profiles_saved.json').read_text()) if (O/'profiles_saved.json').exists() else json.loads((O/'profile_patch.json').read_text())['profiles']
folder=O/'Comparison';folder.mkdir(exist_ok=True);s.render.resolution_x=800;s.render.resolution_y=540
for n in ('M24_Magazine10','M24_bullet','M24_Laser_Lowpoly','M24_LaserHolder_Lowpoly'):
    if n in bpy.data.objects:bpy.data.objects[n].hide_render=True
if 'M24_clip' in bpy.data.objects:bpy.data.objects['M24_clip'].hide_render=False
for label,profiles in (('before',original),('after',new)):
    clip=ue['clips']['idle'];entry=next(c for c in profiles['base'] if c['base']==clip['path']);row,_=local_pose(clip,entry,0);set_pose(row)
    for view in ('side','wrist','palm','fps'):
        if view=='fps':r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
        else:
            r.matrix_world=Matrix.Identity(4);target=base[h].translation if view in ('wrist','palm') else (base[h].translation+base[u].translation)*.5
            off=Vector((-.23,.08,.15)) if view=='wrist' else Vector((.23,-.03,-.10)) if view=='palm' else Vector((-.5,-.14,.20));cam.location=target+root.to_3x3()@off;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.30 if view in ('wrist','palm') else .67
        s.render.filepath=str(folder/(label+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
print('IDLE_COMPARISON_RENDERED',flush=True)
