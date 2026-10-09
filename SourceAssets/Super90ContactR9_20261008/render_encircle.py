from pathlib import Path
O=Path(__file__).parent;src=O/'render_candidate.py'
exec(compile(src.read_text().split('for empty,selected')[0],str(src),'exec'))
fit=ns['json'].loads((O/'hand_encircle.json').read_text());s['hand_in_handle']=ns['Matrix'](fit['loader_hand_in_handle']);s['handle_fingers']={n:ns['Matrix'](v) for n,v in fit['loader_finger_local'].items()};s['pose_cache'].clear()
Vector=ns['Vector'];p,handle,_=s['pose'](87,7,False);ns['apply'](p)
for ob in ns['groups']['props']:ob.hide_render=False
camera=ns['camera'];camera.data.type='ORTHO';camera.data.ortho_scale=.25
for i,at in enumerate(((.20,.08,.07),(-.16,.12,.05),(0,-.18,.09),(0,.20,0))):
    camera.location=handle@Vector(at);target=handle@Vector((0,0,0));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(frames/f'encircle_{i}.png');bpy.ops.render.render(write_still=True)
